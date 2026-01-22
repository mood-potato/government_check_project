import os

import psycopg2
from dotenv import load_dotenv
from qdrant_client import QdrantClient


def get_postgres_connection():
    load_dotenv()

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
    )


def get_qdrant_client() -> QdrantClient:
    """Qdrant 클라이언트 반환"""
    load_dotenv()

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", 6333))

    return QdrantClient(host=host, port=port)