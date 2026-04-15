from typing import Dict, List

from loguru import logger
from sentence_transformers import SentenceTransformer

from modules.base.base_transformer import BaseTransformer


class SpeechVectorizer(BaseTransformer):
    """sentence-transformers로 발언 임베딩 생성"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        logger.info(f"임베딩 모델 로딩: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def transform(self, speeches: List[Dict]) -> List[Dict]:
        """발언 텍스트에 임베딩 벡터 추가"""
        if not speeches:
            return []

        texts = [s.get("text", "") for s in speeches]

        logger.info(f"{len(texts)}건 임베딩 생성 시작")
        embeddings = self.model.encode(texts, show_progress_bar=True)

        results = []
        for speech, embedding in zip(speeches, embeddings):
            speech_with_embedding = speech.copy()
            speech_with_embedding["embedding"] = embedding.tolist()
            results.append(speech_with_embedding)

        logger.info(f"{len(results)}건 임베딩 생성 완료")
        return results

    def encode_query(self, query: str) -> List[float]:
        """검색 쿼리 임베딩 생성"""
        return self.model.encode(query).tolist()
