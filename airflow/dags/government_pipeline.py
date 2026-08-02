"""정부 회의록 데이터 파이프라인을 Airflow에서 실행합니다."""

from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo

from airflow import DAG
from airflow.operators.bash import BashOperator


DEFAULT_ARGS = {
    "owner": "government-check",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email": os.environ.get("PIPELINE_ALERT_EMAIL"),
    "email_on_failure": True,
    "email_on_retry": False,
}


with DAG(
    dag_id="government_check_pipeline",
    description="수집부터 홈 화면 스냅샷까지 단계별로 실행합니다.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Seoul")),
    schedule="0 3 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["government-check", "data-pipeline"],
) as dag:
    speaker_seed = BashOperator(
        task_id="speaker_seed",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages speaker-seed",
    )
    collect_bills = BashOperator(
        task_id="collect_bills",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages bill-url-workbook",
    )
    extract_speeches = BashOperator(
        task_id="extract_speeches",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages bill-speech",
    )
    vectorize = BashOperator(
        task_id="vectorize",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages vectorize",
    )
    find_candidates = BashOperator(
        task_id="find_candidates",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages contradiction",
    )
    refresh_home = BashOperator(
        task_id="refresh_home",
        bash_command="cd /app && uv run python -m pipelines.run_pipeline --stages home",
    )

    speaker_seed >> collect_bills >> extract_speeches >> vectorize >> find_candidates >> refresh_home
