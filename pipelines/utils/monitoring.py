import json
from typing import Any, Dict, Optional

from loguru import logger
from psycopg2.extensions import connection as pg_connection

from pipelines.utils.db import execute_query
from pipelines.utils.schema import load_table_ddl


def ensure_monitoring_tables(connection: pg_connection) -> None:
    """파이프라인 실행/적재 이벤트 모니터링 테이블을 준비합니다.

    Args:
        connection: PostgreSQL 연결 객체입니다.
    """
    execute_query(connection, load_table_ddl("pipeline_monitoring"))


def start_pipeline_run(
    connection: pg_connection,
    pipeline_name: str,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """파이프라인 실행 시작 로그를 기록하고 run_id를 반환합니다.

    Args:
        connection: PostgreSQL 연결 객체입니다.
        pipeline_name: 실행한 파이프라인 이름입니다.
        meta: 실행 설정 등 메타 정보입니다.

    Returns:
        생성된 run_id 문자열입니다.
    """
    query = """
        INSERT INTO pipeline_runs (pipeline_name, status, meta)
        VALUES (%s, 'running', %s::jsonb)
        RETURNING run_id;
    """
    result = execute_query(
        connection,
        query,
        (pipeline_name, json.dumps(meta or {}, ensure_ascii=False)),
    )
    return str(result[0]["run_id"])


def log_load_row_event(
    connection: pg_connection,
    run_id: str,
    target_table: str,
    record_key: str,
    action: str,
    source_date: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """한 row 적재 이벤트를 기록합니다.

    Args:
        connection: PostgreSQL 연결 객체입니다.
        run_id: 파이프라인 실행 ID입니다.
        target_table: 대상 테이블명입니다.
        record_key: 레코드 식별 키 문자열입니다.
        action: inserted/updated/skipped/failed 중 하나입니다.
        source_date: 원천 데이터 기준 날짜입니다.
        meta: 추가 메타 정보입니다.
    """
    query = """
        INSERT INTO pipeline_row_events (
            run_id, target_table, record_key, action, source_date, meta
        )
        VALUES (%s, %s, %s, %s, %s, %s::jsonb);
    """
    execute_query(
        connection,
        query,
        (
            run_id,
            target_table,
            record_key,
            action,
            source_date,
            json.dumps(meta or {}, ensure_ascii=False),
        ),
    )


def finish_pipeline_run(
    connection: pg_connection,
    run_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """파이프라인 실행 종료 상태와 집계 정보를 기록합니다.

    Args:
        connection: PostgreSQL 연결 객체입니다.
        run_id: 파이프라인 실행 ID입니다.
        status: success 또는 failed 상태입니다.
        error_message: 실패 시 에러 메시지입니다.
    """
    aggregate_query = """
        SELECT
            COUNT(*) FILTER (WHERE action = 'inserted') AS inserted_count,
            COUNT(*) FILTER (WHERE action = 'updated') AS updated_count,
            COUNT(*) FILTER (WHERE action = 'skipped') AS skipped_count,
            COUNT(*) FILTER (WHERE action = 'failed') AS failed_count
        FROM pipeline_row_events
        WHERE run_id = %s;
    """
    counts = execute_query(connection, aggregate_query, (run_id,))[0]
    update_query = """
        UPDATE pipeline_runs
        SET
            status = %s,
            finished_at = now(),
            inserted_count = %s,
            updated_count = %s,
            skipped_count = %s,
            failed_count = %s,
            error_message = %s
        WHERE run_id = %s;
    """
    execute_query(
        connection,
        update_query,
        (
            status,
            counts["inserted_count"],
            counts["updated_count"],
            counts["skipped_count"],
            counts["failed_count"],
            error_message,
            run_id,
        ),
    )
    logger.info(f"파이프라인 실행 종료: run_id={run_id}, status={status}")
