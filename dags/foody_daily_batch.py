"""Daily, idempotent Foody batch over local sources and PostgreSQL marts."""

from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.python import PythonOperator

from src.airflow_batch import STAGES, execute_stage

with DAG(
    dag_id="foody_daily_batch",
    description="Quality-gated Sales and Review batch with verified RAG readiness",
    start_date=pendulum.datetime(2026, 11, 1, tz="Asia/Ho_Chi_Minh"),
    schedule="0 2 * * *",
    catchup=False,
    max_active_runs=1,
    render_template_as_native_obj=True,
    default_args={"owner": "foody", "retries": 1,
                  "retry_delay": timedelta(minutes=2),
                  "execution_timeout": timedelta(minutes=30)},
    tags=["foody", "batch", "local"],
) as dag:
    tasks = {}
    for stage in STAGES:
        tasks[stage] = PythonOperator(
            task_id=stage,
            python_callable=execute_stage,
            op_kwargs={
                "stage": stage,
                "run_id": "{{ run_id }}",
                "logical_date": "{{ logical_date.isoformat() }}",
                "quality_fixture": "{{ dag_run.conf.get('quality_fixture') if dag_run and dag_run.conf else none }}",
            },
            retries=0 if stage in {"validate_source", "data_quality_gate"} else 1,
            execution_timeout=timedelta(minutes=90 if stage == "update_rag_indexes" else 30),
        )
    for upstream, downstream in zip(STAGES, STAGES[1:], strict=False):
        tasks[upstream] >> tasks[downstream]
