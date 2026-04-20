import os

import psycopg2
from dotenv import load_dotenv
from elasticsearch import Elasticsearch


def get_postgres_connection():
    load_dotenv()

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