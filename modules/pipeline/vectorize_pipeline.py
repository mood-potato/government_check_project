from loguru import logger

from modules.base.base_pipeline import BasePipeline
from modules.rag.qdrant_loader import QdrantLoader
from modules.rag.speech_extractor import SpeechVectorExtractor
from modules.rag.speech_vectorizer import SpeechVectorizer
from modules.utils.db_connections import get_postgres_connection, get_qdrant_client


class VectorizePipeline(BasePipeline):
    """발언 데이터 벡터화 파이프라인"""

    def __init__(
        self,
        batch_size: int = 1000,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "speeches",
    ):
        """
        Args:
            batch_size: 한 번에 처리할 발언 수
            model_name: 임베딩 모델
            collection_name: Qdrant 컬렉션 이름
        """
        self.pg_connection = get_postgres_connection()
        self.qdrant_client = get_qdrant_client()

        extractor = SpeechVectorExtractor(
            connection=self.pg_connection, batch_size=batch_size
        )
        transformer = SpeechVectorizer(model_name=model_name)
        loader = QdrantLoader(
            client=self.qdrant_client,
            collection_name=collection_name,
        )

        super().__init__(extractor, loader, transformer)

    def run(self) -> int:
        """
        벡터화 파이프라인 실행

        Returns:
            벡터화된 발언 수
        """
        total_vectorized = 0

        # 컬렉션 생성
        self.loader.create_table()

        while True:
            # Step 1: 벡터화되지 않은 발언 추출
            logger.info("✅ 벡터화 대상 발언 추출 시작")
            speeches = self.extractor.extract()

            if not speeches:
                logger.info("✅ 벡터화할 발언이 없습니다.")
                break

            # Step 2: 임베딩 생성
            logger.info(f"✅ {len(speeches)}건 임베딩 생성 시작")
            vectorized_speeches = self.transformer.transform(speeches)

            # Step 3: Qdrant에 저장
            logger.info("✅ Qdrant 저장 시작")
            saved_ids = self.loader.load(vectorized_speeches)

            # Step 4: PostgreSQL에 벡터화 상태 업데이트
            self.extractor.mark_as_vectorized(saved_ids)

            total_vectorized += len(saved_ids)
            logger.info(f"✅ 배치 완료: {len(saved_ids)}건 (총 {total_vectorized}건)")

        logger.info(f"✅ 벡터화 파이프라인 완료: 총 {total_vectorized}건")
        return total_vectorized

    def close(self) -> None:
        """리소스 정리"""
        if self.pg_connection:
            self.pg_connection.close()
        # Qdrant 클라이언트는 별도 close 불필요
