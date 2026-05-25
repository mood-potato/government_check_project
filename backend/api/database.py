import os
from urllib.parse import parse_qs, urlparse

import psycopg2
from dotenv import load_dotenv


def get_postgres_connection():
    """PostgreSQL 연결을 생성한다.

    Supabase 또는 일반 DATABASE_URL이 있으면 연결 문자열을 우선 사용하고,
    없으면 로컬/Compose용 POSTGRES_* 환경변수로 연결한다.

    Returns:
        psycopg2 PostgreSQL 연결 객체.
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
