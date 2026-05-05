import sys

from pipelines.speech_chunk_embedding_pipeline import (
    ElasticsearchSpeechChunkLoader,
    FaissSpeechChunkLoader,
    SpeechChunkEmbeddingTransformer,
    chunk_speech_text,
)


class FakeEmbeddingModel:
    def encode(
        self,
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    ):
        return [[float(len(text)), 1.0] for text in texts]


class FakeElasticsearchClient:
    def __init__(self):
        self.indexed = []
        self.created = []
        self.index_exists = False
        self.indices = self

    def exists(self, index):
        return self.index_exists

    def create(self, index, body):
        self.created.append((index, body))

    def index(self, index, id, document):
        self.indexed.append((index, id, document))


class FakeFaissIndex:
    def __init__(self, dimension):
        self.dimension = dimension
        self.added = []

    def add(self, vectors):
        self.added.append(vectors)


class FakeFaissModule:
    def __init__(self):
        self.indexes = []
        self.written = []

    def IndexFlatIP(self, dimension):
        index = FakeFaissIndex(dimension)
        self.indexes.append(index)
        return index

    def write_index(self, index, path):
        self.written.append((index, path))


def test_chunk_speech_text_keeps_one_whole_speech_record():
    text = "가" * 120 + "나" * 80

    chunks = chunk_speech_text(text, max_chars=100, overlap_chars=20)

    assert [chunk["chunk_index"] for chunk in chunks] == [0]
    assert chunks[0]["text"] == text
    assert chunks[0]["start_char"] == 0
    assert chunks[0]["end_char"] == len(text)


def test_transformer_creates_embeddings_for_speech_chunks():
    speech_text = "국민의 권리 보호가 중요합니다. " * 8
    transformer = SpeechChunkEmbeddingTransformer(
        model=FakeEmbeddingModel(),
        max_chars=80,
        overlap_chars=10,
        batch_size=2,
    )

    chunks = transformer.transform(
        [
            {
                "id": "speech-1",
                "pdf_url_id": "PDF1",
                "speech_number": 7,
                "speaker_id": "member-1",
                "speaker": "홍길동",
                "date": "2026-04-22",
                "title": "법제사법위원회",
                "class_name": "법사위",
                "text": speech_text,
            }
        ]
    )

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "speech-1:0000"
    assert chunks[0]["speech_id"] == "speech-1"
    assert chunks[0]["speaker"] == "홍길동"
    assert chunks[0]["embedding"] == [float(len(speech_text.strip())), 1.0]
    assert chunks[0]["chunk_index"] == 0


def test_elasticsearch_loader_indexes_chunk_documents():
    client = FakeElasticsearchClient()
    loader = ElasticsearchSpeechChunkLoader(
        client=client,
        index_name="speech_chunks",
        vector_size=2,
    )

    loader.create_table()
    saved_ids = loader.load(
        [
            {
                "chunk_id": "speech-1:0000",
                "speech_id": "speech-1",
                "chunk_index": 0,
                "text": "발언 청크",
                "speaker": "홍길동",
                "date": "2026-04-22",
                "title": "회의",
                "class_name": "법사위",
                "embedding": [1.0, 0.0],
            }
        ]
    )

    assert saved_ids == ["speech-1:0000"]
    assert client.created[0][0] == "speech_chunks"
    assert client.created[0][1]["mappings"]["properties"]["embedding"]["dims"] == 2
    assert client.indexed[0][1] == "speech-1:0000"
    assert client.indexed[0][2]["speech_id"] == "speech-1"


def test_faiss_loader_writes_index_and_metadata(tmp_path, monkeypatch):
    fake_faiss = FakeFaissModule()
    monkeypatch.setitem(sys.modules, "faiss", fake_faiss)
    index_path = tmp_path / "speech_chunks.faiss"
    metadata_path = tmp_path / "speech_chunks.jsonl"
    loader = FaissSpeechChunkLoader(
        index_path=index_path,
        metadata_path=metadata_path,
        vector_size=2,
    )

    loader.create_table()
    saved_ids = loader.load(
        [
            {
                "chunk_id": "speech-1:0000",
                "speech_id": "speech-1",
                "chunk_index": 0,
                "text": "발언 청크",
                "embedding": [1.0, 0.0],
            }
        ]
    )

    assert saved_ids == ["speech-1:0000"]
    assert fake_faiss.indexes[0].dimension == 2
    assert fake_faiss.indexes[0].added[0].shape == (1, 2)
    assert fake_faiss.written[0][1] == str(index_path)
    assert '"chunk_id": "speech-1:0000"' in metadata_path.read_text()
