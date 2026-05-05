import os
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import psycopg2
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from loguru import logger
from psycopg2.extensions import connection as pg_connection
from psycopg2.extras import DictCursor, DictRow

from pipelines.utils.common import DatabaseError


def get_postgres_connection():
    """PostgreSQL 연결을 생성합니다.

    `SUPABASE_DATABASE_URL` 또는 `DATABASE_URL`이 있으면 해당 연결 문자열을
    우선 사용합니다. Supabase 원격 DB는 가능한 SSL로 연결해야 하므로 연결
    문자열에 sslmode가 없을 때는 `sslmode=require`를 추가합니다.

    Returns:
        psycopg2 PostgreSQL 연결 객체입니다.
    """
    load_dotenv()

    database_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
    if database_url:
        parsed_url = urlparse(database_url)
        query_params = parse_qs(parsed_url.query)
        connect_kwargs = {}
        if (
            parsed_url.hostname
            and "supabase.com" in parsed_url.hostname
            and "sslmode" not in query_params
        ):
            connect_kwargs["sslmode"] = "require"
        return psycopg2.connect(database_url, **connect_kwargs)

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )


def get_elasticsearch_client() -> Elasticsearch:
    """Elasticsearch 클라이언트 반환"""
    load_dotenv()

    host = os.getenv("ELASTICSEARCH_HOST", "localhost")
    port = int(os.getenv("ELASTICSEARCH_PORT", 9200))

    return Elasticsearch(hosts=[{"host": host, "port": port, "scheme": "http"}])


def execute_query(
    connection: pg_connection,
    query: str,
    params: Optional[Union[Tuple[Any, ...], Dict[str, Any], List[Any]]] = None,
) -> Union[List[DictRow], int]:
    logger.debug(f"Executing query: {query}")
    if params:
        logger.debug(f"With parameters: {params}")

    try:
        with connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(query, params)

            # SELECT 또는 RETURNING 쿼리인 경우 결과 반환
            if (
                query.strip().upper().startswith("SELECT")
                or "RETURNING" in query.upper()
            ):
                result = cursor.fetchall()
                connection.commit()
                return result

            # 그 외 쿼리인 경우 영향받은 행의 수 반환
            connection.commit()
            return cursor.rowcount

    except Exception as e:
        connection.rollback()
        logger.error(f"Query failed: {str(e)}")
        raise DatabaseError(f"Database operation failed: {str(e)}") from e


def update_get_pdf_status(connection, pdf_url_id: str, status: bool) -> None:
    """Update the get_pdf status in the database."""
    query = "UPDATE pdf_url SET get_pdf = %s WHERE pdf_url_id = %s"
    with connection.cursor() as cur:
        cur.execute(query, (status, pdf_url_id))
        connection.commit()
