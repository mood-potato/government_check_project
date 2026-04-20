from contextlib import contextmanager
from typing import Any

from backend.modules.utils.db_connections import get_postgres_connection


class Database:
    _conn = None

    @classmethod
    def get_connection(cls):
        if cls._conn is None or cls._conn.closed:
            cls._conn = get_postgres_connection()
            cls._conn.autocommit = True
        return cls._conn

    @classmethod
    @contextmanager
    def cursor(cls):
        conn = cls.get_connection()
        cur = conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    @classmethod
    def fetch_all(cls, query: str, params: tuple = None) -> list[dict[str, Any]]:
        """Execute query and return list of dicts"""
        with cls.cursor() as cur:
            cur.execute(query, params or ())
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    @classmethod
    def fetch_one(cls, query: str, params: tuple = None) -> dict[str, Any] | None:
        """Execute query and return single dict or None"""
        with cls.cursor() as cur:
            cur.execute(query, params or ())
            columns = [desc[0] for desc in cur.description]
            row = cur.fetchone()
            return dict(zip(columns, row)) if row else None
