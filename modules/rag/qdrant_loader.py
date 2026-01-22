from typing import Any, Dict, List

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from modules.base.base_loader import BaseLoader


class QdrantLoader(BaseLoader):
    """Qdrant에 벡터 데이터 저장"""

    def __init__(
        self,
        client: QdrantClient,
        collection_name: str = "speeches",
        vector_size: int = 384,  # all-MiniLM-L6-v2 기본 차원
    ):
        """
        Args:
            client: Qdrant 클라이언트
            collection_name: 컬렉션 이름
            vector_size: 벡터 차원 (모델에 따라 다름)
        """
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        # BaseLoader는 connection을 받지만, Qdrant에서는 client 사용
        self.connection = None

    def create_table(self) -> None:
        """Qdrant 컬렉션 생성 (없으면)"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Qdrant 컬렉션 '{self.collection_name}' 생성 완료")
        else:
            logger.info(f"Qdrant 컬렉션 '{self.collection_name}' 이미 존재")

    def load(self, vectorized_data: List[Dict]) -> List[int]:
        """
        벡터 데이터를 Qdrant에 저장

        Args:
            vectorized_data: embedding 필드가 포함된 데이터 리스트

        Returns:
            저장된 포인트의 ID 리스트
        """
        if not vectorized_data:
            return []

        points = []
        saved_ids = []

        for data in vectorized_data:
            point_id = data.get("id")
            embedding = data.get("embedding")

            if point_id is None or embedding is None:
                logger.warning(f"id 또는 embedding 누락: {data.keys()}")
                continue

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": data.get("text", ""),
                    "speaker": data.get("speaker", ""),
                    "date": str(data.get("date", "")),
                    "title": data.get("title", ""),
                },
            )
            points.append(point)
            saved_ids.append(point_id)

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            logger.info(f"Qdrant에 {len(points)}건 저장 완료")

        return saved_ids

    def delete_collection(self) -> None:
        """컬렉션 삭제 (테스트/초기화용)"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Qdrant 컬렉션 '{self.collection_name}' 삭제 완료")
        except Exception as e:
            logger.error(f"컬렉션 삭제 실패: {e}")

    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
            }
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return {}
