from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from loguru import logger

from pipelines.transform.speech_vectorizer import SpeechVectorizer


class SpeechSearchService:
    """발언 시맨틱 검색 서비스"""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str = "speeches",
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.client = client
        self.index_name = index_name
        self.vectorizer = SpeechVectorizer(model_name=model_name)

    def search(
        self,
        query: str,
        top_k: int = 10,
        speaker: Optional[str] = None,
        date: Optional[str] = None,
        score_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """시맨틱 검색 수행"""
        query_vector = self.vectorizer.encode_query(query)

        knn: Dict[str, Any] = {
            "field":          "embedding",
            "query_vector":   query_vector,
            "k":              top_k,
            "num_candidates": top_k * 10,
        }

        filters = []
        if speaker:
            filters.append({"term": {"speaker": speaker}})
        if date:
            filters.append({"term": {"date": date}})
        if filters:
            knn["filter"] = {"bool": {"must": filters}}

        try:
            response = self.client.search(
                index=self.index_name,
                knn=knn,
                _source=["text", "speaker", "date", "title"],
            )

            results = []
            for hit in response["hits"]["hits"]:
                score = hit["_score"]
                if score < score_threshold:
                    continue
                results.append(
                    {
                        "id":      hit["_id"],
                        "score":   score,
                        "text":    hit["_source"].get("text", ""),
                        "speaker": hit["_source"].get("speaker", ""),
                        "date":    hit["_source"].get("date", ""),
                        "title":   hit["_source"].get("title", ""),
                    }
                )

            logger.info(f"검색 완료: '{query}' → {len(results)}건")
            return results

        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return []

    def search_by_speaker(self, speaker_name: str, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        return self.search(query=query, top_k=top_k, speaker=speaker_name)

    def search_by_date(self, date: str, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        return self.search(query=query, top_k=top_k, date=date)
