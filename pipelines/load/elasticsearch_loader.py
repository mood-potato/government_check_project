from typing import Any, Dict, List

from elasticsearch import Elasticsearch
from loguru import logger

from pipelines.base.base_loader import BaseLoader


class ElasticsearchLoader(BaseLoader):
    """Elasticsearch에 벡터 데이터 저장"""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str = "speeches",
        vector_size: int = 384,  # all-MiniLM-L6-v2 기본 차원
    ):
        self.client = client
        self.index_name = index_name
        self.vector_size = vector_size
        self.connection = None

    def create_table(self) -> None:
        """Elasticsearch 인덱스 생성 (없으면)"""
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 이미 존재")
            return

        self.client.indices.create(
            index=self.index_name,
            body={
                "mappings": {
                    "properties": {
                        "text":    {"type": "text"},
                        "speaker": {"type": "keyword"},
                        "date":    {"type": "date"},
                        "title":   {"type": "text"},
                        "embedding": {
                            "type":       "dense_vector",
                            "dims":       self.vector_size,
                            "index":      True,
                            "similarity": "cosine",
                        },
                    }
                }
            },
        )
        logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 생성 완료")

    def load(self, vectorized_data: List[Dict]) -> List[Any]:
        """벡터 데이터를 Elasticsearch에 저장"""
        if not vectorized_data:
            return []

        saved_ids = []
        for data in vectorized_data:
            doc_id   = data.get("id")
            embedding = data.get("embedding")

            if doc_id is None or embedding is None:
                logger.warning(f"id 또는 embedding 누락: {data.keys()}")
                continue

            self.client.index(
                index=self.index_name,
                id=doc_id,
                document={
                    "text":      data.get("text", ""),
                    "speaker":   data.get("speaker", ""),
                    "date":      str(data.get("date", "")),
                    "title":     data.get("title", ""),
                    "embedding": embedding,
                },
            )
            saved_ids.append(doc_id)

        if saved_ids:
            logger.info(f"Elasticsearch에 {len(saved_ids)}건 저장 완료")
        return saved_ids

    def delete_index(self) -> None:
        """인덱스 삭제 (테스트/초기화용)"""
        try:
            self.client.indices.delete(index=self.index_name)
            logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 삭제 완료")
        except Exception as e:
            logger.error(f"인덱스 삭제 실패: {e}")

    def get_index_info(self) -> Dict[str, Any]:
        """인덱스 통계 조회"""
        try:
            stats = self.client.indices.stats(index=self.index_name)
            total = stats["_all"]["total"]
            return {
                "name":       self.index_name,
                "doc_count":  total["docs"]["count"],
                "store_size": total["store"]["size_in_bytes"],
            }
        except Exception as e:
            logger.error(f"인덱스 정보 조회 실패: {e}")
            return {}
