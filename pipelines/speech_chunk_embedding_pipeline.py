import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch
from loguru import logger
from sentence_transformers import SentenceTransformer

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.db import get_elasticsearch_client, get_postgres_connection


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_MAX_CHARS = 0
DEFAULT_CHUNK_OVERLAP_CHARS = 0


class SpeechChunkEmbeddingError(Exception):
    """발언 청크 임베딩 처리 중 발생한 오류입니다."""


def _normalize_text(text: str) -> str:
    """청킹 전 공백을 정리합니다."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    return "\n\n".join(lines)


def chunk_speech_text(
    text: str,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> List[Dict[str, Any]]:
    """발언 원문 하나를 통째 임베딩 대상 레코드로 만듭니다.

    Args:
        text: 발언 원문입니다.
        max_chars: 이전 청킹 설정과의 호환용 인자이며 사용하지 않습니다.
        overlap_chars: 이전 청킹 설정과의 호환용 인자이며 사용하지 않습니다.

    Returns:
        발언 전체를 담은 단일 레코드 목록입니다.
    """
    del max_chars, overlap_chars
    normalized_text = _normalize_text(text)
    if not normalized_text:
        return []

    return [
        {
            "chunk_index": 0,
            "text": normalized_text,
            "start_char": 0,
            "end_char": len(normalized_text),
        }
    ]


class SpeechChunkExtractor(BaseExtractor):
    """임베딩할 발언 원문을 PostgreSQL에서 추출합니다."""

    def __init__(self, connection: Any, batch_size: int = 200):
        """추출기를 초기화합니다.

        Args:
            connection: PostgreSQL 연결 객체입니다.
            batch_size: 한 번에 추출할 발언 수입니다.
        """
        self.connection = connection
        self.batch_size = batch_size

    def extract(self) -> List[Dict[str, Any]]:
        """아직 벡터화되지 않은 발언 목록을 가져옵니다.

        Returns:
            발언 메타데이터와 원문을 담은 딕셔너리 목록입니다.
        """
        query = """
            SELECT
                s.id,
                s.pdf_url_id,
                s.speech_number,
                s.speaker_id,
                s.speaker_name AS speaker,
                s.speaker_title,
                s.date,
                s.title,
                s.class_name,
                s.confer_number,
                s.dae_number,
                s.speech AS text
            FROM speeches s
            WHERE s.vectorized = false OR s.vectorized IS NULL
            ORDER BY s.date, s.pdf_url_id, s.speech_number
            LIMIT %s
        """
        with self.connection.cursor() as cur:
            cur.execute(query, (self.batch_size,))
            columns = [description[0] for description in cur.description]
            rows = cur.fetchall()
        results = [dict(zip(columns, row)) for row in rows]
        self.log_info(f"청크 임베딩 대상 발언 {len(results)}건 추출 완료")
        return results

    def mark_as_vectorized(self, speech_ids: List[str]) -> None:
        """임베딩 완료된 발언을 표시합니다.

        Args:
            speech_ids: 완료 처리할 speeches.id 목록입니다.
        """
        if not speech_ids:
            return

        query = "UPDATE speeches SET vectorized = true WHERE id = ANY(%s)"
        with self.connection.cursor() as cur:
            cur.execute(query, (speech_ids,))
        self.connection.commit()
        self.log_info(f"청크 임베딩 완료 발언 {len(speech_ids)}건 표시")


class SpeechChunkEmbeddingTransformer(BaseTransformer):
    """발언 전체 단위 임베딩을 생성합니다."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        model: Optional[Any] = None,
        max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
        overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
        batch_size: int = 32,
        normalize_embeddings: bool = True,
    ):
        """변환기를 초기화합니다.

        Args:
            model_name: sentence-transformers 모델 이름입니다.
            model: 테스트나 주입용 임베딩 모델입니다.
            max_chars: 이전 청킹 설정과의 호환용 값입니다.
            overlap_chars: 이전 청킹 설정과의 호환용 값입니다.
            batch_size: 임베딩 생성 배치 크기입니다.
            normalize_embeddings: 코사인 유사도 계산을 위해 벡터를 정규화할지 여부입니다.
        """
        self.model_name = model_name
        self.model = model if model is not None else SentenceTransformer(model_name)
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings

    def transform(self, speeches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """발언 목록을 임베딩된 발언 단위 레코드 목록으로 변환합니다.

        Args:
            speeches: 발언 row 목록입니다.

        Returns:
            발언 메타데이터와 embedding 필드를 포함한 목록입니다.
        """
        chunk_records = []
        for speech in speeches:
            speech_id = str(speech["id"])
            chunks = chunk_speech_text(
                speech.get("text", ""),
                max_chars=self.max_chars,
                overlap_chars=self.overlap_chars,
            )
            for chunk in chunks:
                chunk_id = f"{speech_id}:{chunk['chunk_index']:04d}"
                chunk_records.append(
                    {
                        "chunk_id": chunk_id,
                        "speech_id": speech_id,
                        "pdf_url_id": speech.get("pdf_url_id"),
                        "speech_number": speech.get("speech_number"),
                        "speaker_id": speech.get("speaker_id"),
                        "speaker": speech.get("speaker"),
                        "speaker_title": speech.get("speaker_title"),
                        "date": str(speech.get("date", "")),
                        "title": speech.get("title"),
                        "class_name": speech.get("class_name"),
                        "confer_number": speech.get("confer_number"),
                        "dae_number": speech.get("dae_number"),
                        "chunk_index": chunk["chunk_index"],
                        "start_char": chunk["start_char"],
                        "end_char": chunk["end_char"],
                        "text": chunk["text"],
                    }
                )

        if not chunk_records:
            return []

        texts = [record["text"] for record in chunk_records]
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=self.normalize_embeddings,
        )
        for record, embedding in zip(chunk_records, embeddings):
            if hasattr(embedding, "tolist"):
                record["embedding"] = embedding.tolist()
            else:
                record["embedding"] = list(embedding)

        self.log_info(f"발언 {len(chunk_records)}건 임베딩 생성 완료")
        return chunk_records


class ElasticsearchSpeechChunkLoader(BaseLoader):
    """임베딩된 발언 청크를 Elasticsearch에 저장합니다."""

    def __init__(
        self,
        client: Elasticsearch,
        index_name: str = "speech_chunks",
        vector_size: int = 384,
    ):
        """로더를 초기화합니다.

        Args:
            client: Elasticsearch 클라이언트입니다.
            index_name: 저장할 인덱스 이름입니다.
            vector_size: 임베딩 차원 수입니다.
        """
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
                        "speech_id": {"type": "keyword"},
                        "pdf_url_id": {"type": "keyword"},
                        "speech_number": {"type": "integer"},
                        "chunk_index": {"type": "integer"},
                        "speaker_id": {"type": "keyword"},
                        "speaker": {"type": "keyword"},
                        "speaker_title": {"type": "keyword"},
                        "date": {"type": "date"},
                        "title": {"type": "text"},
                        "class_name": {"type": "keyword"},
                        "text": {"type": "text"},
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

    def load(self, chunk_records: List[Dict[str, Any]]) -> List[str]:
        """청크 문서를 Elasticsearch에 저장합니다.

        Args:
            chunk_records: embedding 필드가 포함된 청크 목록입니다.

        Returns:
            저장된 chunk_id 목록입니다.
        """
        saved_ids = []
        for record in chunk_records:
            chunk_id = record.get("chunk_id")
            embedding = record.get("embedding")
            if not chunk_id or embedding is None:
                logger.warning(f"chunk_id 또는 embedding 누락: {record.keys()}")
                continue

            self.client.index(
                index=self.index_name,
                id=chunk_id,
                document={
                    "speech_id": record.get("speech_id"),
                    "pdf_url_id": record.get("pdf_url_id"),
                    "speech_number": record.get("speech_number"),
                    "chunk_index": record.get("chunk_index"),
                    "speaker_id": record.get("speaker_id"),
                    "speaker": record.get("speaker"),
                    "speaker_title": record.get("speaker_title"),
                    "date": record.get("date"),
                    "title": record.get("title"),
                    "class_name": record.get("class_name"),
                    "start_char": record.get("start_char"),
                    "end_char": record.get("end_char"),
                    "text": record.get("text", ""),
                    "embedding": embedding,
                },
            )
            saved_ids.append(str(chunk_id))

        logger.info(f"Elasticsearch에 발언 청크 {len(saved_ids)}건 저장 완료")
        return saved_ids


class JsonlSpeechChunkLoader(BaseLoader):
    """임베딩된 발언 청크를 로컬 JSONL 파일에 저장합니다."""

    def __init__(self, output_path: Path):
        """로더를 초기화합니다.

        Args:
            output_path: JSONL 출력 경로입니다.
        """
        self.output_path = output_path
        self.connection = None

    def create_table(self) -> None:
        """출력 디렉터리를 준비합니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, chunk_records: List[Dict[str, Any]]) -> List[str]:
        """청크 목록을 JSONL 파일에 append합니다.

        Args:
            chunk_records: 저장할 청크 목록입니다.

        Returns:
            저장된 chunk_id 목록입니다.
        """
        saved_ids = []
        with self.output_path.open("a", encoding="utf-8") as output_file:
            for record in chunk_records:
                chunk_id = record.get("chunk_id")
                if not chunk_id:
                    continue
                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                saved_ids.append(str(chunk_id))
        return saved_ids


class FaissSpeechChunkLoader(BaseLoader):
    """임베딩된 발언 청크를 로컬 FAISS 인덱스로 저장합니다."""

    def __init__(
        self,
        index_path: Path,
        metadata_path: Path,
        vector_size: int,
    ):
        """로더를 초기화합니다.

        Args:
            index_path: FAISS 인덱스 파일 경로입니다.
            metadata_path: FAISS row 순서와 chunk_id를 매핑할 JSONL 경로입니다.
            vector_size: 임베딩 차원 수입니다.
        """
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.vector_size = vector_size
        self.connection = None
        self._index = None

    def create_table(self) -> None:
        """인덱스와 메타데이터 출력 디렉터리를 준비합니다."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_faiss_index(self):
        """FAISS IndexFlatIP 인스턴스를 생성하거나 재사용합니다.

        Returns:
            FAISS 인덱스 객체입니다.

        Raises:
            SpeechChunkEmbeddingError: faiss-cpu가 설치되지 않은 경우입니다.
        """
        if self._index is not None:
            return self._index

        try:
            import faiss
        except ImportError as error:
            raise SpeechChunkEmbeddingError(
                "FAISS 인덱스를 저장하려면 faiss-cpu 패키지가 필요합니다."
            ) from error

        self._index = faiss.IndexFlatIP(self.vector_size)
        return self._index

    def load(self, chunk_records: List[Dict[str, Any]]) -> List[str]:
        """청크 임베딩을 FAISS 인덱스와 JSONL 메타데이터로 저장합니다.

        Args:
            chunk_records: embedding 필드가 포함된 청크 목록입니다.

        Returns:
            저장된 chunk_id 목록입니다.

        Raises:
            SpeechChunkEmbeddingError: numpy 또는 faiss-cpu가 없거나 차원이 맞지 않는 경우입니다.
        """
        valid_records = [
            record
            for record in chunk_records
            if record.get("chunk_id") and record.get("embedding") is not None
        ]
        if not valid_records:
            return []

        try:
            import numpy as np
        except ImportError as error:
            raise SpeechChunkEmbeddingError(
                "FAISS 벡터 저장을 위해 numpy 패키지가 필요합니다."
            ) from error

        vectors = np.asarray(
            [record["embedding"] for record in valid_records],
            dtype="float32",
        )
        if vectors.ndim != 2 or vectors.shape[1] != self.vector_size:
            raise SpeechChunkEmbeddingError(
                f"임베딩 차원이 일치하지 않습니다: expected={self.vector_size}, "
                f"actual={vectors.shape}"
            )

        index = self._get_faiss_index()
        index.add(vectors)

        with self.metadata_path.open("a", encoding="utf-8") as metadata_file:
            for record in valid_records:
                metadata = {
                    key: value
                    for key, value in record.items()
                    if key != "embedding"
                }
                metadata_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")

        import faiss

        faiss.write_index(index, str(self.index_path))
        saved_ids = [str(record["chunk_id"]) for record in valid_records]
        logger.info(f"FAISS 인덱스에 발언 청크 {len(saved_ids)}건 저장 완료")
        return saved_ids


class CompositeSpeechChunkLoader(BaseLoader):
    """여러 청크 로더에 같은 데이터를 함께 저장합니다."""

    def __init__(self, loaders: List[BaseLoader]):
        """복합 로더를 초기화합니다.

        Args:
            loaders: 순서대로 실행할 로더 목록입니다.
        """
        self.loaders = loaders
        self.connection = None

    def create_table(self) -> None:
        """모든 하위 로더의 저장소를 준비합니다."""
        for loader in self.loaders:
            loader.create_table()

    def load(self, chunk_records: List[Dict[str, Any]]) -> List[str]:
        """모든 하위 로더에 청크 목록을 저장합니다.

        Args:
            chunk_records: 저장할 청크 목록입니다.

        Returns:
            첫 번째 로더가 저장한 chunk_id 목록입니다.
        """
        saved_ids = []
        for loader in self.loaders:
            current_saved_ids = loader.load(chunk_records)
            if not saved_ids:
                saved_ids = current_saved_ids
        return saved_ids


class SpeechChunkEmbeddingPipeline(BasePipeline):
    """발언 원문을 청크 임베딩으로 만드는 파이프라인입니다."""

    def __init__(
        self,
        batch_size: int = 200,
        model_name: str = DEFAULT_MODEL_NAME,
        index_name: str = "speech_chunks",
        max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
        overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
        embedding_batch_size: int = 32,
        vector_size: int = 384,
        faiss_index_path: Optional[Path] = None,
        faiss_metadata_path: Optional[Path] = None,
    ):
        """파이프라인 구성요소를 초기화합니다.

        Args:
            batch_size: DB에서 한 번에 읽을 발언 수입니다.
            model_name: sentence-transformers 모델 이름입니다.
            index_name: Elasticsearch 인덱스 이름입니다.
            max_chars: 청크 최대 문자 수입니다.
            overlap_chars: 청크 겹침 문자 수입니다.
            embedding_batch_size: 임베딩 모델 배치 크기입니다.
            vector_size: Elasticsearch dense_vector 차원 수입니다.
            faiss_index_path: 함께 저장할 FAISS 인덱스 경로입니다.
            faiss_metadata_path: FAISS row 메타데이터 JSONL 경로입니다.
        """
        self.pg_connection = get_postgres_connection()
        self.es_client = get_elasticsearch_client()

        extractor = SpeechChunkExtractor(
            connection=self.pg_connection,
            batch_size=batch_size,
        )
        transformer = SpeechChunkEmbeddingTransformer(
            model_name=model_name,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            batch_size=embedding_batch_size,
        )
        elasticsearch_loader = ElasticsearchSpeechChunkLoader(
            client=self.es_client,
            index_name=index_name,
            vector_size=vector_size,
        )
        loaders: List[BaseLoader] = [elasticsearch_loader]
        if faiss_index_path is not None and faiss_metadata_path is not None:
            loaders.append(
                FaissSpeechChunkLoader(
                    index_path=faiss_index_path,
                    metadata_path=faiss_metadata_path,
                    vector_size=vector_size,
                )
            )
        loader = (
            loaders[0]
            if len(loaders) == 1
            else CompositeSpeechChunkLoader(loaders=loaders)
        )
        super().__init__(extractor, loader, transformer)

    def run(self) -> int:
        """발언 청크 임베딩 파이프라인을 실행합니다.

        Returns:
            저장된 청크 수입니다.
        """
        total_chunks = 0
        self.loader.create_table()

        while True:
            speeches = self.extractor.extract()
            if not speeches:
                break

            chunk_records = self.transformer.transform(speeches)
            saved_chunk_ids = self.loader.load(chunk_records)
            saved_speech_ids = sorted(
                {chunk_id.split(":", 1)[0] for chunk_id in saved_chunk_ids}
            )
            self.extractor.mark_as_vectorized(saved_speech_ids)
            total_chunks += len(saved_chunk_ids)
            logger.info(
                f"발언 청크 임베딩 배치 완료: {len(saved_chunk_ids)}건"
                f" (총 {total_chunks}건)"
            )

        return total_chunks

    def close(self) -> None:
        """PostgreSQL 연결 리소스를 정리합니다."""
        if self.pg_connection:
            self.pg_connection.close()
