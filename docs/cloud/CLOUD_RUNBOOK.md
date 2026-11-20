# Cloud RAW runbook

Run from the repository root. First create the S3 bucket in the chosen region
with public access blocked and versioning enabled. Create the two scoped AWS
IAM roles/policies described in `AWS_IAM_POLICY.md`. A Snowflake administrator
must create/configure a storage integration and complete its AWS trust. The
integration may only read `s3://<bucket>/<prefix>/raw/`.

Set the required variables in the current shell or a private credential
provider. The example values below are placeholders, **not** live IDs:

```powershell
$env:AWS_REGION = 'ap-southeast-1'
$env:FOODY_S3_BUCKET = '<your-bucket>'
$env:FOODY_S3_PREFIX = 'foody'
$env:SNOWFLAKE_ACCOUNT = '<account-identifier>'
$env:SNOWFLAKE_USER = '<ingest-user>'
$env:SNOWFLAKE_ROLE = 'FOODY_INGEST_ROLE'
$env:SNOWFLAKE_WAREHOUSE = 'FOODY_WH'
$env:SNOWFLAKE_DATABASE = 'FOODY'
$env:SNOWFLAKE_RAW_SCHEMA = 'RAW'
$env:SNOWFLAKE_STAGING_SCHEMA = 'STAGING'
$env:SNOWFLAKE_MART_SCHEMA = 'MART'
$env:SNOWFLAKE_STORAGE_INTEGRATION = 'FOODY_S3_INTEGRATION'
# Set SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_FILE privately.
# Use the AWS SDK credential chain: AWS_PROFILE, temporary env credentials,
# or an IAM role. Do not put keys in Git.
```

```powershell
python -m pip install -r requirements-cloud.txt
python -m scripts.cloud_foundation inspect
python -m scripts.cloud_foundation bootstrap-sql
# Review the rendered SQL and stage URL, then set SNOWFLAKE_BOOTSTRAP_ROLE.
python -m scripts.cloud_foundation bootstrap
python -m scripts.cloud_foundation upload
python -m scripts.cloud_foundation run
python -m scripts.cloud_foundation run  # idempotency check
```

`upload` only writes S3. `run` validates both accepted CSVs, verifies/registers
S3 objects, COPY loads RAW and audits counts. Inspect
`outputs/cloud/runs/<batch_id>.json` and Snowflake `FOODY.RAW.LOAD_AUDIT`.
After the second `run`, S3 and Snowflake should report `SKIPPED_DUPLICATE`.
Do not treat a failed `upload` as a completed cloud acceptance.

For optional Airflow use, prepare private `.env.cloud` with the same variables,
`SNOWFLAKE_DBT_ROLE=FOODY_TRANSFORM_ROLE`, `SNOWFLAKE_PASSWORD`, and
`FOODY_CLOUD_DBT_ENABLED=true`. The cloud DAG now requires the dbt transform
and quality gate; follow `docs/dbt/DBT_RUNBOOK.md` before triggering it.
Use short-lived AWS environment credentials. A host `AWS_PROFILE` alone is
insufficient inside the container unless its profile files are separately
mounted read-only. Then:

```powershell
$files = @('-f','docker-compose.yml','-f','docker-compose.devops.yml','-f','docker-compose.airflow.yml')
docker compose @files --profile airflow build airflow
docker compose @files -f docker-compose.cloud.yml --profile airflow build airflow
docker compose @files -f docker-compose.cloud.yml --profile airflow up -d airflow
docker compose @files -f docker-compose.cloud.yml --profile airflow exec -T airflow airflow dags trigger foody_cloud_raw
```

The cloud DAG stays paused/manual and rejects triggers unless the dbt opt-in
is enabled. The accepted `foody_daily_batch` local DAG
and PostgreSQL service continue to work. The cloud image is optional; do not
start it for ordinary local demos. Run `docker compose @files config --quiet`
for the unchanged local stack.
