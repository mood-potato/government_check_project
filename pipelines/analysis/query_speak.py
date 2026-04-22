import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch


DEFAULT_INDEX_NAME = "comitee_meetings"
DEFAULT_SPEAKER_NAME = "교육위원장 김영호"


def get_elasticsearch_client() -> Elasticsearch:
    load_dotenv()
    elastic_password = os.getenv("ELASTIC_SEARCH_PW")
    return Elasticsearch(
        "https://localhost:9200",
        basic_auth=("elastic", elastic_password),
        verify_certs=False,
    )


def get_speaker_documents(
    speaker_name: str = DEFAULT_SPEAKER_NAME,
    client: Elasticsearch | None = None,
    index_name: str = DEFAULT_INDEX_NAME,
):
    query = {
        "query": {
            "match": {
                "speaker": speaker_name
            }
        }
    }

    es_client = client or get_elasticsearch_client()
    res = es_client.search(index=index_name, body=query, size=100)
    return res["hits"]["hits"]


def main() -> None:
    documents = get_speaker_documents()
    for doc in documents:
        print(f"문서 ID: {doc['_id']}, 내용: {doc['_source']}")


if __name__ == "__main__":
    main()
