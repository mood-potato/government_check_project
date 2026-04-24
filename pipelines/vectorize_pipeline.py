from typing import Any, Dict, List

from elasticsearch import Elasticsearch
from loguru import logger
from sentence_transformers import SentenceTransformer

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.db import get_elasticsearch_client, get_postgres_connection


class SpeechVectorExtractor(BaseExtractor):
    """벡터화되지 않은 speeches row를 추출합니다."""

    def __init__(self, connection: Any, batch_size: int = 1000):
        self.connection = connection
        self.batch_size = batch_size

    def extract(self) -> List[Dict]:
        """벡터화되지 않은 발언 데이터를 추출합니다.

        Returns:
            벡터화 대상 발언 row 목록입니다.
        """
        query = """
            SELECT
                s.id,
                s.speech as text,
                COALESCE(sp.name, s.speaker_name) as speaker,
                s.date,
                s.title
            FROM speeches s
            LEFT JOIN speakers sp ON s.speaker_id = sp.id
            WHERE s.vectorized = false OR s.vectorized IS NULL
            LIMIT %s
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(query, (self.batch_size,))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                self.log_info(f"벡터화 대상 {len(results)}건 추출 완료")
                return results
        except Exception as e:
            logger.error(f"발언 추출 중 오류: {e}")
            return []

    def mark_as_vectorized(self, speech_ids: List[str]) -> None:
        """벡터화 완료된 발언 상태를 업데이트합니다.

        Args:
            speech_ids: 벡터화가 완료된 speeches ID 목록입니다.
        """
        if not speech_ids:
            return

        query = "UPDATE speeches SET vectorized = true WHERE id = ANY(%s)"
        try:
            with self.connection.cursor() as cur:
                cur.execute(query, (speech_ids,))
                self.connection.commit()
                logger.info(f"{len(speech_ids)}건 벡터화 상태 업데이트 완료")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"벡터화 상태 업데이트 실패: {e}")


class SpeechVectorizer(BaseTransformer):
    """sentence-transformers로 발언 임베딩을 생성합니다."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        logger.info(f"임베딩 모델 로딩: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def transform(self, speeches: List[Dict]) -> List[Dict]:
        """발언 텍스트에 임베딩 벡터를 추가합니다.

        Args:
            speeches: 발언 row 목록입니다.

        Returns:
            embedding 필드가 추가된 발언 row 목록입니다.
        """
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
        """검색 쿼리 임베딩을 생성합니다.

        Args:
            query: 검색어입니다.

        Returns:
            검색어 임베딩 벡터입니다.
        """
        return self.model.encode(query).tolist()


class ElasticsearchLoader(BaseLoader):
    """Elasticsearch에 벡터 데이터를 저장합니다."""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str = "speeches",
        vector_size: int = 384,
    ):
        self.client = client
        self.index_name = index_name
        self.vector_size = vector_size
        self.connection = None

    def create_table(self) -> None:
        """Elasticsearch 인덱스를 생성합니다."""
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 이미 존재")
            return

        self.client.indices.create(
            index=self.index_name,
            body={
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "speaker": {"type": "keyword"},
                        "date": {"type": "date"},
                        "title": {"type": "text"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": self.vector_size,
                            "index": True,
                            "similarity": "cosine",
                        },
                    }
                }
            },
        )
        logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 생성 완료")

    def load(self, vectorized_data: List[Dict]) -> List[Any]:
        """벡터 데이터를 Elasticsearch에 저장합니다.

        Args:
            vectorized_data: embedding 필드가 포함된 발언 row 목록입니다.

        Returns:
            Elasticsearch 저장에 성공한 문서 ID 목록입니다.
        """
        if not vectorized_data:
            return []

        saved_ids = []
        for data in vectorized_data:
            doc_id = data.get("id")
            embedding = data.get("embedding")

            if doc_id is None or embedding is None:
                logger.warning(f"id 또는 embedding 누락: {data.keys()}")
                continue

            self.client.index(
                index=self.index_name,
                id=doc_id,
                document={
                    "text": data.get("text", ""),
                    "speaker": data.get("speaker", ""),
                    "date": str(data.get("date", "")),
                    "title": data.get("title", ""),
                    "embedding": embedding,
                },
            )
            saved_ids.append(doc_id)

        if saved_ids:
            logger.info(f"Elasticsearch에 {len(saved_ids)}건 저장 완료")
        return saved_ids

    def delete_index(self) -> None:
        """테스트나 초기화를 위해 인덱스를 삭제합니다."""
        try:
            self.client.indices.delete(index=self.index_name)
            logger.info(f"Elasticsearch 인덱스 '{self.index_name}' 삭제 완료")
        except Exception as e:
            logger.error(f"인덱스 삭제 실패: {e}")

    def get_index_info(self) -> Dict[str, Any]:
        """인덱스 통계를 조회합니다.

        Returns:
            인덱스 이름, 문서 수, 저장소 크기 정보입니다.
        """
        try:
            stats = self.client.indices.stats(index=self.index_name)
            total = stats["_all"]["total"]
            return {
                "name": self.index_name,
                "doc_count": total["docs"]["count"],
                "store_size": total["store"]["size_in_bytes"],
            }
        except Exception as e:
            logger.error(f"인덱스 정보 조회 실패: {e}")
            return {}


class VectorizePipeline(BasePipeline):
    """발언 데이터 벡터화 파이프라인입니다."""

    def __init__(
        self,
        batch_size: int = 1000,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_name: str = "speeches",
    ):
        """파이프라인 구성요소를 초기화합니다.

        Args:
            batch_size: 한 번에 처리할 발언 수입니다.
            model_name: 임베딩 모델 이름입니다.
            index_name: Elasticsearch 인덱스 이름입니다.
        """
        self.pg_connection = get_postgres_connection()
        self.es_client = get_elasticsearch_client()

        extractor = SpeechVectorExtractor(
            connection=self.pg_connection, batch_size=batch_size
        )
        transformer = SpeechVectorizer(model_name=model_name)
        loader = ElasticsearchLoader(
            client=self.es_client,
            index_name=index_name,
        )

        super().__init__(extractor, loader, transformer)

    def run(self) -> int:
        """벡터화 파이프라인을 실행합니다.

        Returns:
            벡터화된 발언 수입니다.
        """
        total_vectorized = 0

        self.loader.create_table()

        while True:
            logger.info("✅ 벡터화 대상 발언 추출 시작")
            speeches = self.extractor.extract()

            if not speeches:
                logger.info("✅ 벡터화할 발언이 없습니다.")
                break

            logger.info(f"✅ {len(speeches)}건 임베딩 생성 시작")
            vectorized_speeches = self.transformer.transform(speeches)

            logger.info("✅ Elasticsearch 저장 시작")
            saved_ids = self.loader.load(vectorized_speeches)

            self.extractor.mark_as_vectorized(saved_ids)

            total_vectorized += len(saved_ids)
            logger.info(f"✅ 배치 완료: {len(saved_ids)}건 (총 {total_vectorized}건)")

        logger.info(f"✅ 벡터화 파이프라인 완료: 총 {total_vectorized}건")
        return total_vectorized

    def close(self) -> None:
        """PostgreSQL 연결 리소스를 정리합니다."""
        if self.pg_connection:
            self.pg_connection.close()
