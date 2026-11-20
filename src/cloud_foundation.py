"""Optional, quality-gated Foody CSV -> S3 -> Snowflake RAW ingestion.

Cloud SDKs are imported only by live operations. The local PostgreSQL and
Airflow paths do not depend on AWS or Snowflake packages or credentials.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.foody.review_paths import DATA_VERSION
from src.foody.review_paths import SOURCE as REVIEW_SOURCE
from src.foody.schema import digest
from src.sales.audit import SOURCE as SALES_SOURCE

OUTPUT = Path("outputs/cloud/runs")
SOURCES = {
    "sales": {"path": SALES_SOURCE, "version": "sales_orders_v1", "table": "SALES_SOURCE",
              "columns": ("ORDER_ID", "ORDER_DATE", "SALES_AMOUNT", "ORDER_STATUS",
                          "RESTAURANT_ID", "RESTAURANT_NAME")},
    "reviews": {"path": REVIEW_SOURCE, "version": DATA_VERSION, "table": "REVIEWS_SOURCE",
                "columns": ("REVIEW_TIME", "RATING", "COMMENT", "RESTAURANT_ID",
                            "RESTAURANT_NAME", "ADDRESS")},
}
IDENTIFIER = re.compile(r"[A-Z][A-Z0-9_]*\Z")
BUCKET = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]\Z")
PREFIX = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_/-]*\Z")


def _identifier(value):
    value = value.strip().upper()
    if not IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid Snowflake identifier in cloud configuration")
    return value


@dataclass(frozen=True)
class CloudConfig:
    region: str
    bucket: str
    prefix: str = "foody"
    account: str = ""
    user: str = ""
    role: str = "FOODY_INGEST_ROLE"
    warehouse: str = "FOODY_WH"
    database: str = "FOODY"
    raw_schema: str = "RAW"
    staging_schema: str = "STAGING"
    mart_schema: str = "MART"
    integration: str = "FOODY_S3_INTEGRATION"

    def __post_init__(self):
        if not BUCKET.fullmatch(self.bucket) or ".." in self.bucket:
            raise ValueError("FOODY_S3_BUCKET must be a valid DNS-style S3 bucket name")
        if not self.region or not re.fullmatch(r"[a-z]{2}-[a-z-]+-\d", self.region):
            raise ValueError("AWS_REGION must be an AWS region such as ap-southeast-1")
        if not PREFIX.fullmatch(self.prefix) or ".." in self.prefix or "//" in self.prefix:
            raise ValueError("FOODY_S3_PREFIX must contain safe path components")
        object.__setattr__(self, "prefix", self.prefix.strip("/"))
        for name in ("role", "warehouse", "database", "raw_schema", "staging_schema",
                     "mart_schema", "integration"):
            object.__setattr__(self, name, _identifier(getattr(self, name)))

    @classmethod
    def from_env(cls):
        return cls(region=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "")),
                   bucket=os.getenv("FOODY_S3_BUCKET", ""),
                   prefix=os.getenv("FOODY_S3_PREFIX", "foody"),
                   account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
                   user=os.getenv("SNOWFLAKE_USER", ""),
                   role=os.getenv("SNOWFLAKE_ROLE", "FOODY_INGEST_ROLE"),
                   warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "FOODY_WH"),
                   database=os.getenv("SNOWFLAKE_DATABASE", "FOODY"),
                   raw_schema=os.getenv("SNOWFLAKE_RAW_SCHEMA", "RAW"),
                   staging_schema=os.getenv("SNOWFLAKE_STAGING_SCHEMA", "STAGING"),
                   mart_schema=os.getenv("SNOWFLAKE_MART_SCHEMA", "MART"),
                   integration=os.getenv("SNOWFLAKE_STORAGE_INTEGRATION",
                                     "FOODY_S3_INTEGRATION"))

    def require_snowflake(self):
        if not self.account or not self.user:
            raise ValueError("SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER are required")
        if not (os.getenv("SNOWFLAKE_PASSWORD") or os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE")):
            raise ValueError("Set SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_FILE")

    @property
    def stage(self):
        return f"{self.database}.{self.raw_schema}.FOODY_S3_STAGE"

    @property
    def audit_table(self):
        return f"{self.database}.{self.raw_schema}.LOAD_AUDIT"


def source_metadata(name, *, path=None):
    """Validate the accepted source with the existing project audits."""
    if name not in SOURCES:
        raise ValueError("Unknown cloud source")
    spec = SOURCES[name]
    path = Path(path or spec["path"])
    if name == "sales":
        from src.sales.audit import audit_orders, require_loadable

        audit = audit_orders(path)
        require_loadable(audit)
        row_count, date_min, date_max = audit["rows"], audit["date_min"], audit["date_max"]
    else:
        from src.foody.review_migration import audit_source, read_source, require_accepted

        frame = read_source(path)
        audit = audit_source(frame)
        # The original acceptance also checks the Sales ID/name namespace.
        from src.foody.review_migration import align_ids
        from src.sales.audit import read_orders

        require_accepted(audit, align_ids(frame, read_orders(SALES_SOURCE)))
        row_count, date_min, date_max = audit["rows"], audit["date_min"], audit["date_max"]
    return {"source": name, "original_filename": path.name, "path": str(path),
            "size_bytes": path.stat().st_size, "row_count": int(row_count),
            "sha256": digest(path), "source_version": spec["version"],
            "date_min": date_min, "date_max": date_max}


def plan_sources():
    sources = {name: source_metadata(name) for name in SOURCES}
    # Match the accepted local Airflow batch identity: Review hash first.
    joined = f"{sources['reviews']['sha256']}:{sources['sales']['sha256']}"
    batch_id = hashlib.sha256(joined.encode()).hexdigest()[:20]
    for source in sources.values():
        source["batch_id"] = batch_id
    return sources


def object_key(config, source):
    if source["source"] not in SOURCES or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]):
        raise ValueError("Invalid source name or SHA256")
    filename = source["original_filename"]
    if Path(filename).name != filename or not re.fullmatch(r"[a-zA-Z0-9_.-]+\.csv", filename):
        raise ValueError("Unsafe CSV filename")
    version = SOURCES[source["source"]]["version"]
    return (f"{config.prefix}/raw/{source['source']}/version={version}/"
            f"sha256={source['sha256']}/{filename}")


def manifest_key(config, source):
    return f"{config.prefix}/manifests/{source['source']}/{source['sha256']}.json"


def _head(s3, bucket, key):
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except Exception as error:
        code = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        if code in {"403", "AccessDenied"}:
            # Prefix-scoped ListBucket may not grant HEAD's missing-key 404.
            listed = s3.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
            if not any(item["Key"] == key for item in listed.get("Contents", [])):
                return None
        raise


def upload_source(config, source, s3):
    """Upload one immutable CSV and register its hash in an S3 manifest."""
    key, mkey = object_key(config, source), manifest_key(config, source)
    prior = _head(s3, config.bucket, mkey)
    if prior:
        manifest = json.loads(s3.get_object(Bucket=config.bucket, Key=mkey)["Body"].read())
        raw = _head(s3, config.bucket, key)
        if (manifest["sha256"] != source["sha256"] or
                manifest["row_count"] != source["row_count"] or
                manifest["size_bytes"] != source["size_bytes"] or
                manifest["object_key"] != key or
                manifest["source_version"] != source["source_version"] or
                manifest["original_filename"] != source["original_filename"] or not raw or
                raw["ContentLength"] != source["size_bytes"] or
                raw.get("Metadata", {}).get("sha256") != source["sha256"]):
            raise ValueError("Registered S3 manifest/object differs from accepted source")
        return {**manifest, "status": "SKIPPED_DUPLICATE"}
    existing = _head(s3, config.bucket, key)
    if existing and (existing["ContentLength"] != source["size_bytes"] or
                     existing.get("Metadata", {}).get("sha256") != source["sha256"]):
        raise ValueError("Existing S3 object differs from accepted source")
    if not existing:
        s3.upload_file(source["path"], config.bucket, key,
                       ExtraArgs={"ServerSideEncryption": "AES256",
                                  "Metadata": {"sha256": source["sha256"]}})
    manifest = {key_: source[key_] for key_ in ("source", "original_filename", "size_bytes",
                                               "row_count", "sha256", "source_version", "batch_id",
                                               "date_min", "date_max")}
    manifest.update({"object_key": key, "manifest_key": mkey,
                     "uploaded_at_utc": datetime.now(UTC).isoformat()})
    try:
        s3.put_object(Bucket=config.bucket, Key=mkey,
                      Body=json.dumps(manifest, ensure_ascii=False).encode(),
                      ContentType="application/json", ServerSideEncryption="AES256",
                      IfNoneMatch="*")
    except Exception as error:
        code = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
        if code not in {"PreconditionFailed", "412"}:
            raise
        return upload_source(config, source, s3)
    return {**manifest, "status": "NEW"}


def copy_sql(config, source, key):
    """Return a fixed-shape COPY statement; no user text becomes SQL syntax."""
    expected = object_key(config, source)
    if key != expected:
        raise ValueError("S3 key does not match validated source")
    relative = key.removeprefix(config.prefix + "/")
    columns = SOURCES[source["source"]]["columns"]
    select = ", ".join(f"t.${number}" for number in range(1, len(columns) + 1))
    targets = ", ".join((*columns, "SOURCE_FILE"))
    return (f"COPY INTO TEMP_FOODY_RAW ({targets}) FROM (SELECT {select}, "
            f"METADATA$FILENAME FROM @{config.stage}/{relative} t) "
            f"FILE_FORMAT=(FORMAT_NAME={config.database}.{config.raw_schema}.FOODY_CSV) "
            "ON_ERROR=ABORT_STATEMENT")


def load_source(config, source, manifest, conn):
    """COPY into a temporary table, validate, then atomically publish one batch."""
    table = f"{config.database}.{config.raw_schema}.{SOURCES[source['source']]['table']}"
    if manifest["sha256"] != source["sha256"] or manifest["row_count"] != source["row_count"]:
        raise ValueError("S3 manifest does not reconcile with local accepted source")
    key = manifest["object_key"]
    sql = copy_sql(config, source, key)
    cursor = conn.cursor()
    cursor.execute(f"SELECT ROW_COUNT, SOURCE_HASH FROM {config.audit_table} "
                   "WHERE SOURCE_NAME=%s AND BATCH_ID=%s",
                   (source["source"], source["batch_id"]))
    prior = cursor.fetchone()
    if prior:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE BATCH_ID=%s", (source["batch_id"],))
        if prior[0] != source["row_count"] or prior[1] != source["sha256"] or (
                cursor.fetchone()[0] != source["row_count"]):
            raise ValueError("Existing Snowflake batch audit or RAW rows differ")
        return {"status": "SKIPPED_DUPLICATE", "source": source["source"],
                "batch_id": source["batch_id"], "rows_loaded": 0, "rows_rejected": 0}
    columns = SOURCES[source["source"]]["columns"]
    definition = ", ".join(f"{name} VARCHAR" for name in (*columns, "SOURCE_FILE"))
    cursor.execute(f"CREATE OR REPLACE TEMP TABLE TEMP_FOODY_RAW ({definition})")
    cursor.execute(sql)
    copy_id = cursor.sfqid
    copy_rows = cursor.fetchall()
    rejected = sum(int(row[5] or 0) for row in copy_rows)
    copied = sum(int(row[3] or 0) for row in copy_rows)
    cursor.execute("SELECT COUNT(*) FROM TEMP_FOODY_RAW")
    staged = cursor.fetchone()[0]
    if rejected or copied != staged or staged != source["row_count"]:
        raise ValueError("Snowflake COPY row count or error count differs from source")
    id_column = "ORDER_ID" if source["source"] == "sales" else "RESTAURANT_ID"
    date_column = "ORDER_DATE" if source["source"] == "sales" else "REVIEW_TIME"
    date_format = "YYYY-MM-DD" if source["source"] == "sales" else "DD/MM/YYYY"
    cursor.execute(f"SELECT COUNT_IF({id_column} IS NULL OR TRIM({id_column})=''), "
                   f"COUNT_IF(TRY_TO_DATE({date_column}, '{date_format}') IS NULL), "
                   f"MIN(TRY_TO_DATE({date_column}, '{date_format}')), "
                   f"MAX(TRY_TO_DATE({date_column}, '{date_format}')) FROM TEMP_FOODY_RAW")
    null_ids, invalid_dates, date_min, date_max = cursor.fetchone()
    if (null_ids or invalid_dates or str(date_min) != source["date_min"] or
            str(date_max) != source["date_max"]):
        raise ValueError("Snowflake staged IDs or date range failed quality gate")
    if source["source"] == "sales":
        cursor.execute("SELECT COUNT_IF(TRY_TO_DOUBLE(SALES_AMOUNT) IS NULL OR "
                       "TRY_TO_DOUBLE(SALES_AMOUNT)<0), "
                       "COUNT_IF(ORDER_STATUS NOT IN ('Delivered','Cancelled','Refunded') "
                       "OR ORDER_STATUS IS NULL), "
                       "COUNT(*)-COUNT(DISTINCT ORDER_ID) FROM TEMP_FOODY_RAW")
    else:
        cursor.execute("SELECT COUNT_IF(TRY_TO_DOUBLE(RATING) IS NULL OR "
                       "TRY_TO_DOUBLE(RATING)<0 OR TRY_TO_DOUBLE(RATING)>10), "
                       "COUNT_IF(RESTAURANT_NAME IS NULL OR ADDRESS IS NULL), "
                       "COUNT_IF(TRY_TO_NUMBER(RESTAURANT_ID) IS NULL) "
                       "FROM TEMP_FOODY_RAW")
    if any(cursor.fetchone()):
        raise ValueError("Snowflake staged numeric, status or identifier quality failed")
    columns_sql = ", ".join(columns)
    try:
        cursor.execute("BEGIN")
        cursor.execute(f"SELECT COUNT(*) FROM {config.audit_table} "
                       "WHERE SOURCE_NAME=%s AND BATCH_ID=%s",
                       (source["source"], source["batch_id"]))
        if cursor.fetchone()[0]:
            raise ValueError("Concurrent Snowflake batch detected; retry after audit")
        cursor.execute(f"INSERT INTO {table} ({columns_sql}, SOURCE_FILE, SOURCE_HASH, "
                       f"BATCH_ID, LOADED_AT) SELECT {columns_sql}, SOURCE_FILE, %s, %s, "
                       "CURRENT_TIMESTAMP() FROM TEMP_FOODY_RAW",
                       (source["sha256"], source["batch_id"]))
        insert_id = cursor.sfqid
        cursor.execute(f"INSERT INTO {config.audit_table} "
                       "(SOURCE_NAME, BATCH_ID, SOURCE_HASH, SOURCE_FILE, S3_OBJECT_KEY, "
                       "ROW_COUNT, REJECTED_ROWS, COPY_QUERY_ID, INSERT_QUERY_ID, LOADED_AT) "
                       "VALUES (%s,%s,%s,%s,%s,%s,0,%s,%s,CURRENT_TIMESTAMP())",
                       (source["source"], source["batch_id"], source["sha256"],
                        source["original_filename"], key, staged, copy_id, insert_id))
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE BATCH_ID=%s AND SOURCE_HASH=%s",
                       (source["batch_id"], source["sha256"]))
        if cursor.fetchone()[0] != staged:
            raise ValueError("Snowflake RAW post-insert count failed")
        cursor.execute("COMMIT")
    except Exception:
        cursor.execute("ROLLBACK")
        raise
    return {"status": "NEW", "source": source["source"],
            "batch_id": source["batch_id"], "object_key": key,
            "copy_query_id": copy_id, "insert_query_id": insert_id,
            "rows_loaded": staged, "rows_rejected": rejected}


def _write_audit(batch_id, record):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / f"{batch_id}.json"
    temporary = target.with_name(target.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    return target


def s3_client(config):
    import boto3

    return boto3.client("s3", region_name=config.region)


def snowflake_connection(config, *, bootstrap=False):
    import snowflake.connector

    config.require_snowflake()
    kwargs = {"account": config.account, "user": config.user, "role": config.role,
              "autocommit": True,
              "session_parameters": {"QUERY_TAG": "foody_cloud_raw_foundation"}}
    if not bootstrap:
        kwargs.update({"warehouse": config.warehouse, "database": config.database,
                       "schema": config.raw_schema})
    if password := os.getenv("SNOWFLAKE_PASSWORD"):
        kwargs["password"] = password
    else:
        kwargs["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
        if phrase := os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE_PWD"):
            kwargs["private_key_file_pwd"] = phrase
    return snowflake.connector.connect(**kwargs)


def run_cloud(config, *, mode="run", s3=None, conn=None):
    """Validate both sources, upload immutable objects, and optionally load RAW."""
    if mode not in {"upload", "run"}:
        raise ValueError("Cloud mode must be upload or run")
    sources = plan_sources()
    batch_id = sources["sales"]["batch_id"]
    record = {"batch_id": batch_id, "started_at_utc": datetime.now(UTC).isoformat(),
              "status": "RUNNING", "sources": {
                  name: {"source_hash": source["sha256"],
                         "source_version": source["source_version"],
                         "source_rows": source["row_count"], "status": "PENDING"}
                  for name, source in sources.items()}, "error_category": None,
              "failed_source": None}
    current_source = None
    try:
        if mode == "run":
            config.require_snowflake()
        s3 = s3 or s3_client(config)
        if mode == "run":
            conn = conn or snowflake_connection(config)
        for name, source in sources.items():
            current_source = name
            uploaded = upload_source(config, source, s3)
            entry = record["sources"][name]
            entry.update({"s3": uploaded, "status": "UPLOADED"})
            _write_audit(batch_id, record)
            if mode == "run":
                entry["snowflake"] = load_source(config, source, uploaded, conn)
                entry["status"] = "LOADED"
                _write_audit(batch_id, record)
        record["status"] = "SUCCESS"
    except Exception as error:
        from src.security.audit import security_event

        security_event("cloud_ingestion", type(error).__name__, request_id=batch_id)
        record["status"] = "FAILED"
        record["error_category"] = type(error).__name__
        record["failed_source"] = current_source
        raise
    finally:
        record["ended_at_utc"] = datetime.now(UTC).isoformat()
        _write_audit(batch_id, record)
        if mode == "run" and conn is not None:
            conn.close()
    return record


def render_bootstrap(config):
    template = (Path(__file__).resolve().parents[1] / "sql/snowflake/bootstrap.sql")
    sql = template.read_text(encoding="utf-8")
    values = {"DATABASE": config.database, "WAREHOUSE": config.warehouse,
              "RAW": config.raw_schema, "STAGING": config.staging_schema,
              "MART": config.mart_schema, "INTEGRATION": config.integration,
              "BUCKET": config.bucket, "PREFIX": config.prefix}
    for key, value in values.items():
        sql = sql.replace("{{" + key + "}}", value)
    return sql
