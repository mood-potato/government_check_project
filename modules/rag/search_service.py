from typing import Any, Dict, List, Optional

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from modules.rag.speech_vectorizer import SpeechVectorizer


class SpeechSearchService:
    """발언 시맨틱 검색 서비스"""

    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str = "speeches",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Args:
            qdrant_client: Qdrant 클라이언트
            collection_name: 검색할 컬렉션 이름
            model_name: 쿼리 임베딩에 사용할 모델
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.vectorizer = SpeechVectorizer(model_name=model_name)

    def search(
        self,
        query: str,
        top_k: int = 10,
        speaker: Optional[str] = None,
        date: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        시맨틱 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
            speaker: 발언자 필터 (선택)
            date: 날짜 필터 (선택)
            score_threshold: 최소 유사도 점수

        Returns:
            검색 결과 리스트 (score, text, speaker, date, title 포함)
        """
        # 쿼리 임베딩 생성
        query_vector = self.vectorizer.encode_query(query)

        # 필터 조건 구성
        filter_conditions = []
        if speaker:
            filter_conditions.append(
                FieldCondition(key="speaker", match=MatchValue(value=speaker))
            )
        if date:
            filter_conditions.append(
                FieldCondition(key="date", match=MatchValue(value=date))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        try:
            # Qdrant 검색 수행
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )

            # 결과 변환
            search_results = []
            for hit in results:
                search_results.append(
                    {
                        "id": hit.id,
                        "score": hit.score,
                        "text": hit.payload.get("text", ""),
                        "speaker": hit.payload.get("speaker", ""),
                        "date": hit.payload.get("date", ""),
                        "title": hit.payload.get("title", ""),
                    }
                )

            logger.info(f"검색 완료: '{query}' → {len(search_results)}건")
            return search_results

        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return []

    def search_by_speaker(
        self, speaker_name: str, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        특정 발언자의 발언에서 검색

        Args:
            speaker_name: 발언자 이름
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        return self.search(query=query, top_k=top_k, speaker=speaker_name)

    def search_by_date(
        self, date: str, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        특정 날짜의 발언에서 검색

        Args:
            date: 날짜 (YYYY-MM-DD 형식)
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        return self.search(query=query, top_k=top_k, date=date)

    def get_similar_speeches(
        self, speech_id: int, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        특정 발언과 유사한 발언 찾기

        Args:
            speech_id: 기준 발언 ID
            top_k: 반환할 최대 결과 수

        Returns:
            유사 발언 리스트
        """
        try:
            # 기준 발언의 벡터 가져오기
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[speech_id],
                with_vectors=True,
            )

            if not points:
                logger.warning(f"발언 ID {speech_id}를 찾을 수 없습니다.")
                return []

            # 유사 발언 검색 (자기 자신 제외를 위해 top_k + 1)
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=points[0].vector,
                limit=top_k + 1,
            )

            # 자기 자신 제외
            similar = [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.payload.get("text", ""),
                    "speaker": hit.payload.get("speaker", ""),
                    "date": hit.payload.get("date", ""),
                    "title": hit.payload.get("title", ""),
                }
                for hit in results
                if hit.id != speech_id
            ][:top_k]

            return similar

        except Exception as e:
            logger.error(f"유사 발언 검색 중 오류: {e}")
            return []
