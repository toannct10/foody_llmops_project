"""Offline tests for the optional cloud RAW foundation."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from src import cloud_foundation as cloud


def config():
    return cloud.CloudConfig(region="ap-southeast-1", bucket="foody-test-bucket")


def source(name="sales"):
    return {"source": name, "path": f"/tmp/{name}.csv", "original_filename": f"{name}.csv",
            "sha256": "a" * 64, "size_bytes": 100, "row_count": 2,
            "source_version": cloud.SOURCES[name]["version"], "batch_id": "batch-1",
            "date_min": "2025-01-01", "date_max": "2025-01-02"}


class MissingKey(Exception):
    response = {"Error": {"Code": "404"}}


class ForbiddenKey(Exception):
    response = {"Error": {"Code": "403"}}


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.upload_count = 0

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise MissingKey
        obj = self.objects[Key]
        return {"ContentLength": len(obj["body"]), "Metadata": obj.get("metadata", {})}

    def upload_file(self, path, bucket, key, ExtraArgs):
        self.upload_count += 1
        self.objects[key] = {"body": b"x" * 100, "metadata": ExtraArgs["Metadata"]}

    def put_object(self, *, Bucket, Key, Body, **kwargs):
        assert Key not in self.objects
        self.objects[Key] = {"body": Body}

    def get_object(self, *, Bucket, Key):
        from io import BytesIO

        return {"Body": BytesIO(self.objects[Key]["body"])}

    def list_objects_v2(self, *, Bucket, Prefix, MaxKeys):
        return {"Contents": [{"Key": key} for key in self.objects if key == Prefix]}


def test_prefix_scoped_iam_missing_head_is_checked_with_list():
    class PrefixS3(FakeS3):
        def head_object(self, *, Bucket, Key):
            if Key not in self.objects:
                raise ForbiddenKey
            return super().head_object(Bucket=Bucket, Key=Key)

    s3 = PrefixS3()
    result = cloud.upload_source(config(), source(), s3)
    assert result["status"] == "NEW"


def test_s3_key_generation_and_safe_config():
    item = source()
    key = cloud.object_key(config(), item)
    assert key == f"foody/raw/sales/version=sales_orders_v1/sha256={'a' * 64}/sales.csv"
    assert cloud.manifest_key(config(), item) == f"foody/manifests/sales/{'a' * 64}.json"
    with pytest.raises(ValueError, match="identifier"):
        cloud.CloudConfig(region="ap-southeast-1", bucket="foody-test-bucket",
                          database="FOODY;DROP DATABASE X")
    with pytest.raises(ValueError, match="bucket"):
        cloud.CloudConfig(region="ap-southeast-1", bucket="Bad_Bucket")
    with pytest.raises(ValueError, match="filename"):
        cloud.object_key(config(), {**item, "original_filename": "../evil.csv"})


def test_source_hash_and_validation_reuse_existing_audit(tmp_path, monkeypatch):
    path = tmp_path / "sales.csv"
    path.write_text("content", encoding="utf-8")
    from src.sales import audit

    monkeypatch.setattr(audit, "audit_orders", lambda candidate: {
        "rows": 2, "date_min": "2025-01-01", "date_max": "2025-01-02"})
    monkeypatch.setattr(audit, "require_loadable", lambda report: None)
    metadata = cloud.source_metadata("sales", path=path)
    assert metadata["sha256"] == cloud.digest(path)
    assert metadata["row_count"] == 2
    assert metadata["source_version"] == "sales_orders_v1"


def test_cloud_batch_id_matches_accepted_local_airflow_order(monkeypatch):
    hashes = {"sales": "6ba29ff7641b75a623a1e5e8a83b65d3578ba2eda01c443bf9eb8e3f451435cf",
              "reviews": "4a5e4cc1d7b1f9eb9b2d392e551545e6c3b9082bbc8dfe01ddf17002aea8e787"}
    monkeypatch.setattr(cloud, "source_metadata",
                        lambda name: {**source(name), "sha256": hashes[name]})
    planned = cloud.plan_sources()
    assert planned["sales"]["batch_id"] == "896d0b521a4ee20edd60"
    assert planned["reviews"]["batch_id"] == planned["sales"]["batch_id"]


def test_s3_upload_deduplicates_and_detects_mismatch():
    s3 = FakeS3()
    item = source()
    first = cloud.upload_source(config(), item, s3)
    second = cloud.upload_source(config(), item, s3)
    assert first["status"] == "NEW"
    assert second["status"] == "SKIPPED_DUPLICATE"
    assert s3.upload_count == 1
    assert json.loads(s3.objects[cloud.manifest_key(config(), item)]["body"])["sha256"] == item["sha256"]
    s3.objects[first["object_key"]]["metadata"]["sha256"] = "bad"
    with pytest.raises(ValueError, match="differs"):
        cloud.upload_source(config(), item, s3)


def test_cloud_upload_writes_machine_audit_without_credentials(tmp_path, monkeypatch):
    items = {name: source(name) for name in ("sales", "reviews")}
    monkeypatch.setattr(cloud, "plan_sources", lambda: items)
    monkeypatch.setattr(cloud, "OUTPUT", tmp_path)
    s3 = FakeS3()
    first = cloud.run_cloud(config(), mode="upload", s3=s3)
    second = cloud.run_cloud(config(), mode="upload", s3=s3)
    assert first["status"] == second["status"] == "SUCCESS"
    assert first["sources"]["sales"]["s3"]["status"] == "NEW"
    assert second["sources"]["sales"]["s3"]["status"] == "SKIPPED_DUPLICATE"
    assert json.loads((tmp_path / "batch-1.json").read_text())["status"] == "SUCCESS"


def test_bootstrap_and_copy_sql_use_actual_source_mapping():
    sql = cloud.render_bootstrap(config())
    assert "CREATE WAREHOUSE IF NOT EXISTS FOODY_WH" in sql
    assert "CREATE SCHEMA IF NOT EXISTS FOODY.STAGING" in sql
    assert "FOODY_AI_READONLY_ROLE" in sql
    assert "REVIEW_TIME VARCHAR, RATING VARCHAR, COMMENT VARCHAR" in sql
    item = source("reviews")
    copy = cloud.copy_sql(config(), item, cloud.object_key(config(), item))
    assert "REVIEW_TIME, RATING, COMMENT, RESTAURANT_ID" in copy
    assert "METADATA$FILENAME" in copy
    assert "ON_ERROR=ABORT_STATEMENT" in copy
    with pytest.raises(ValueError, match="key"):
        cloud.copy_sql(config(), item, "foody/raw/evil.csv")


def test_bootstrap_connection_does_not_require_uncreated_database(monkeypatch):
    captured = {}
    snowflake = ModuleType("snowflake")
    connector = ModuleType("snowflake.connector")
    connector.connect = lambda **kwargs: captured.update(kwargs)
    snowflake.connector = connector
    monkeypatch.setitem(sys.modules, "snowflake", snowflake)
    monkeypatch.setitem(sys.modules, "snowflake.connector", connector)
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "example-only")
    admin = cloud.CloudConfig(region="ap-southeast-1", bucket="foody-test-bucket",
                              account="test-account", user="test-user", role="ACCOUNTADMIN")
    cloud.snowflake_connection(admin, bootstrap=True)
    assert captured["role"] == "ACCOUNTADMIN"
    assert "warehouse" not in captured and "database" not in captured
    cloud.snowflake_connection(admin)
    assert captured["warehouse"] == "FOODY_WH" and captured["schema"] == "RAW"


class FakeCursor:
    def __init__(self, *, existing=False):
        self.existing = existing
        self.calls = []
        self.sfqid = "query-id"
        self.last = ""

    def execute(self, sql, params=None):
        self.last = sql
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        sql = self.last
        if "SELECT ROW_COUNT, SOURCE_HASH" in sql:
            return (2, "a" * 64) if self.existing else None
        if "SELECT COUNT_IF" in sql:
            if "TRY_TO_DOUBLE" in sql:
                return (0, 0, 0)
            return (0, 0, "2025-01-01", "2025-01-02")
        if "SELECT COUNT(*)" in sql:
            if "LOAD_AUDIT" in sql:
                return (0,)
            return (2,)
        raise AssertionError(sql)

    def fetchall(self):
        return [("sales.csv", "LOADED", 2, 2, 1, 0, None)]


class FakeConn:
    def __init__(self, *, existing=False):
        self.c = FakeCursor(existing=existing)

    def cursor(self):
        return self.c


def test_snowflake_load_is_idempotent_and_checks_counts():
    item = source()
    manifest = {**item, "object_key": cloud.object_key(config(), item)}
    conn = FakeConn()
    result = cloud.load_source(config(), item, manifest, conn)
    assert result["status"] == "NEW" and result["rows_loaded"] == 2
    assert any(sql == "COMMIT" for sql, _ in conn.c.calls)
    second = FakeConn(existing=True)
    duplicate = cloud.load_source(config(), item, manifest, second)
    assert duplicate["status"] == "SKIPPED_DUPLICATE"
    assert not any(sql.startswith("COPY INTO") for sql, _ in second.c.calls)
    with pytest.raises(ValueError, match="manifest"):
        cloud.load_source(config(), item, {**manifest, "sha256": "bad"}, conn)


def test_cloud_dag_is_optional_and_wired(monkeypatch):
    created, dependencies = {}, []

    class FakeDag:
        def __init__(self, **kwargs):
            created.update(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeOperator:
        def __init__(self, **kwargs):
            self.task_id = kwargs["task_id"]
            created.setdefault("tasks", {})[self.task_id] = kwargs

        def __rshift__(self, other):
            dependencies.append((self.task_id, other.task_id))
            return other

    airflow = ModuleType("airflow")
    airflow.DAG = FakeDag
    operators = ModuleType("airflow.operators")
    python = ModuleType("airflow.operators.python")
    python.PythonOperator = FakeOperator
    pendulum = ModuleType("pendulum")
    pendulum.datetime = lambda *args, **kwargs: (args, kwargs)
    for name, module in (("airflow", airflow), ("airflow.operators", operators),
                         ("airflow.operators.python", python), ("pendulum", pendulum)):
        monkeypatch.setitem(sys.modules, name, module)
    path = Path(__file__).resolve().parents[1] / "dags/foody_cloud_raw.py"
    spec = importlib.util.spec_from_file_location("test_cloud_dag", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert created["dag_id"] == "foody_cloud_raw"
    assert created["schedule"] is None
    assert created["is_paused_upon_creation"] is True
    assert dependencies == [("detect_source", "validate_source"),
                            ("validate_source", "upload_s3"),
                            ("upload_s3", "load_snowflake_raw"),
                            ("load_snowflake_raw", "dbt_run"),
                            ("dbt_run", "dbt_test"),
                            ("dbt_test", "quality_gate"),
                            ("quality_gate", "publish")]
    assert created["default_args"]["retries"] == 0
