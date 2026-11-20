"""Optional, paused S3 -> Snowflake RAW DAG; local batch is untouched."""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.cloud_dbt import dbt_run as run_dbt_models
from src.cloud_dbt import dbt_test as test_dbt_models
from src.cloud_dbt import publish_ready as publish_dbt_ready
from src.cloud_dbt import quality_gate as check_dbt_quality
from src.cloud_dbt import require_enabled
from src.cloud_foundation import (
    CloudConfig,
    load_source,
    plan_sources,
    s3_client,
    snowflake_connection,
    upload_source,
)
from src.security.audit import security_event


def detect_source():
    require_enabled()
    return plan_sources()


def validate_source(**context):
    detected = context["ti"].xcom_pull(task_ids="detect_source")
    current = plan_sources()
    if detected != current:
        raise ValueError("Source changed between cloud detection and validation")
    return current


def upload_s3(**context):
    try:
        config = CloudConfig.from_env()
        sources = context["ti"].xcom_pull(task_ids="validate_source")
        s3 = s3_client(config)
        return {name: upload_source(config, source, s3) for name, source in sources.items()}
    except Exception as error:
        security_event("cloud_ingestion", type(error).__name__,
                       request_id=context.get("run_id"))
        raise


def load_snowflake_raw(**context):
    try:
        config = CloudConfig.from_env()
        config.require_snowflake()
        sources = context["ti"].xcom_pull(task_ids="validate_source")
        uploaded = context["ti"].xcom_pull(task_ids="upload_s3")
        with snowflake_connection(config) as conn:
            return {name: load_source(config, source, uploaded[name], conn)
                    for name, source in sources.items()}
    except Exception as error:
        security_event("cloud_ingestion", type(error).__name__,
                       request_id=context.get("run_id"))
        raise


def dbt_run():
    return run_dbt_models()


def dbt_test():
    return test_dbt_models()


def quality_gate():
    return check_dbt_quality()


def publish(**context):
    ti = context["ti"]
    return publish_dbt_ready(
        dag_run_id=context["run_id"],
        sources=ti.xcom_pull(task_ids="validate_source"),
        loads=ti.xcom_pull(task_ids="load_snowflake_raw"),
        gate=ti.xcom_pull(task_ids="quality_gate"),
    )


with DAG(
    dag_id="foody_cloud_raw",
    description="Optional quality-gated Foody S3 and Snowflake RAW load",
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Ho_Chi_Minh"),
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    max_active_runs=1,
    default_args={"owner": "foody", "retries": 0,
                  "retry_delay": timedelta(minutes=2),
                  "execution_timeout": timedelta(minutes=30)},
    tags=["foody", "cloud", "optional"],
) as dag:
    detect = PythonOperator(task_id="detect_source", python_callable=detect_source)
    validate = PythonOperator(task_id="validate_source", python_callable=validate_source)
    upload = PythonOperator(task_id="upload_s3", python_callable=upload_s3,
                            retries=1, execution_timeout=timedelta(minutes=45))
    load = PythonOperator(task_id="load_snowflake_raw", python_callable=load_snowflake_raw,
                          retries=1, execution_timeout=timedelta(minutes=45))
    run = PythonOperator(task_id="dbt_run", python_callable=dbt_run,
                         retries=1, execution_timeout=timedelta(minutes=70))
    test = PythonOperator(task_id="dbt_test", python_callable=dbt_test,
                          retries=1, execution_timeout=timedelta(minutes=70))
    gate = PythonOperator(task_id="quality_gate", python_callable=quality_gate)
    ready = PythonOperator(task_id="publish", python_callable=publish)
    detect >> validate >> upload >> load >> run >> test >> gate >> ready
