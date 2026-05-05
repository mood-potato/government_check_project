from pathlib import Path

from pipelines.pdf_to_speech_pipeline import (
    BillURLToSpeechPipeline,
    BillURLToSpeechExtractor,
    PDFToSpeechPipeline,
    update_bill_url_get_pdf_status,
)


class FakePage:
    def extract_text(self):
        return "◯위원장 서영교 안건을 상정합니다."


class FakePDF:
    pages = [FakePage()]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class RecordingCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class RecordingConnection:
    def __init__(self):
        self.cursor_obj = RecordingCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_bill_url_extractor_reads_local_pdf_without_http(monkeypatch, tmp_path):
    pdf_path = tmp_path / "minutes.pdf"
    pdf_path.write_bytes(b"%PDF-1.7")
    opened_paths = []

    def fake_pdf_open(path):
        opened_paths.append(Path(path))
        return FakePDF()

    class FailingHTTPClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise AssertionError("local bill_url PDF should not use HTTP")

    monkeypatch.setattr("pipelines.pdf_to_speech_pipeline.pdfplumber.open", fake_pdf_open)
    monkeypatch.setattr("pipelines.pdf_to_speech_pipeline.httpx.Client", FailingHTTPClient)

    result = BillURLToSpeechExtractor(connection=object()).extract_one(
        {
            "bill_url_id": "BILLURL1",
            "download_url": str(pdf_path),
            "agenda_name": "방송법 일부개정법률안",
            "meeting_date": "2026-04-09",
            "meeting_type": "상임위원회 회의록",
            "confer_number": 3,
            "dae_number": 22,
        }
    )

    assert opened_paths == [pdf_path]
    assert result["pdf_url_id"] == "bill_url:BILLURL1"
    assert result["bill_url_id"] == "BILLURL1"
    assert result["title"] == "방송법 일부개정법률안"
    assert result["date"] == "2026-04-09"
    assert result["class_name"] == "상임위원회 회의록"
    assert result["confer_number"] == 3
    assert result["dae_number"] == 22
    assert "안건을 상정합니다" in result["text"]
    assert result["file_path"] == str(pdf_path)


def test_update_bill_url_get_pdf_status_updates_bill_url_table():
    connection = RecordingConnection()

    update_bill_url_get_pdf_status(connection, "BILLURL1", True)

    assert connection.cursor_obj.executed == [
        ("UPDATE bill_url SET get_pdf = %s WHERE id = %s", (True, "BILLURL1"))
    ]
    assert connection.committed is True


def test_pdf_to_speech_pipeline_processes_one_pdf_at_a_time(monkeypatch):
    events = []

    class Extractor:
        def fetch_pdf_urls(self):
            events.append("fetch")
            return [
                {
                    "pdf_url_id": "PDF1",
                    "pdf_url": "https://example.com/1.pdf",
                    "title": "회의1",
                    "date": "2026-04-01",
                    "class_name": "본회의",
                    "confer_number": 1,
                    "dae_number": 22,
                },
                {
                    "pdf_url_id": "PDF2",
                    "pdf_url": "https://example.com/2.pdf",
                    "title": "회의2",
                    "date": "2026-04-02",
                    "class_name": "본회의",
                    "confer_number": 2,
                    "dae_number": 22,
                },
            ]

        def extract(self):
            raise AssertionError("pipeline should not materialize all PDFs")

        def extract_one(self, row):
            events.append(f"extract:{row['pdf_url_id']}")
            return {
                **row,
                "text": f"◯의원 홍길동 {row['title']} 발언",
                "file_path": row["pdf_url"],
            }

    class Transformer:
        def transform(self, **kwargs):
            events.append(f"transform:{kwargs['pdf_url_id']}")
            return [
                {
                    "pdf_url_id": kwargs["pdf_url_id"],
                    "speaker": "홍길동",
                    "speaker_title": "의원",
                    "date": kwargs["date"],
                    "title": kwargs["title"],
                    "class_name": kwargs["class_name"],
                    "confer_number": kwargs["confer_number"],
                    "dae_number": kwargs["dae_number"],
                    "text": kwargs["text"],
                    "summary": None,
                    "timestamp": "2026-04-01T00:00:00",
                }
            ]

    class Loader:
        def load(self, speech_data):
            events.append(f"load:{speech_data[0]['pdf_url_id']}")

    updates = []
    monkeypatch.setattr(
        "pipelines.pdf_to_speech_pipeline.update_get_pdf_status",
        lambda connection, pdf_url_id, status: updates.append((pdf_url_id, status)),
    )

    pipeline = object.__new__(PDFToSpeechPipeline)
    pipeline.extractor = Extractor()
    pipeline.transformer = Transformer()
    pipeline.loader = Loader()
    pipeline.connection = object()

    pipeline.run()

    assert events == [
        "fetch",
        "extract:PDF1",
        "transform:PDF1",
        "load:PDF1",
        "extract:PDF2",
        "transform:PDF2",
        "load:PDF2",
    ]
    assert updates == [("PDF1", True), ("PDF2", True)]


def test_bill_url_to_speech_pipeline_processes_one_pdf_at_a_time(monkeypatch):
    events = []

    class Extractor:
        def fetch_bill_urls(self):
            events.append("fetch")
            return [
                {
                    "bill_url_id": "BILLURL1",
                    "download_url": "https://example.com/1.pdf",
                    "agenda_name": "안건1",
                    "meeting_date": "2026-04-01",
                    "meeting_type": "상임위원회",
                    "confer_number": 1,
                    "dae_number": 22,
                },
                {
                    "bill_url_id": "BILLURL2",
                    "download_url": "https://example.com/2.pdf",
                    "agenda_name": "안건2",
                    "meeting_date": "2026-04-02",
                    "meeting_type": "상임위원회",
                    "confer_number": 2,
                    "dae_number": 22,
                },
            ]

        def extract(self):
            raise AssertionError("pipeline should not materialize all PDFs")

        def extract_one(self, row):
            events.append(f"extract:{row['bill_url_id']}")
            return {
                "pdf_url_id": f"bill_url:{row['bill_url_id']}",
                "bill_url_id": row["bill_url_id"],
                "title": row["agenda_name"],
                "date": row["meeting_date"],
                "class_name": row["meeting_type"],
                "confer_number": row["confer_number"],
                "dae_number": row["dae_number"],
                "text": f"◯의원 홍길동 {row['agenda_name']} 발언",
                "file_path": row["download_url"],
            }

    class Transformer:
        def transform(self, **kwargs):
            events.append(f"transform:{kwargs['pdf_url_id']}")
            return [
                {
                    "pdf_url_id": kwargs["pdf_url_id"],
                    "speaker": "홍길동",
                    "speaker_title": "의원",
                    "date": kwargs["date"],
                    "title": kwargs["title"],
                    "class_name": kwargs["class_name"],
                    "confer_number": kwargs["confer_number"],
                    "dae_number": kwargs["dae_number"],
                    "text": kwargs["text"],
                    "summary": None,
                    "timestamp": "2026-04-01T00:00:00",
                }
            ]

    class Loader:
        def create_table(self):
            events.append("create_table")

        def load(self, speech_data):
            events.append(f"load:{speech_data[0]['pdf_url_id']}")

    updates = []
    monkeypatch.setattr(
        "pipelines.pdf_to_speech_pipeline.update_bill_url_get_pdf_status",
        lambda connection, bill_url_id, status: updates.append((bill_url_id, status)),
    )

    pipeline = object.__new__(BillURLToSpeechPipeline)
    pipeline.extractor = Extractor()
    pipeline.transformer = Transformer()
    pipeline.loader = Loader()
    pipeline.connection = object()

    pipeline.run()

    assert events == [
        "fetch",
        "create_table",
        "extract:BILLURL1",
        "transform:bill_url:BILLURL1",
        "load:bill_url:BILLURL1",
        "extract:BILLURL2",
        "transform:bill_url:BILLURL2",
        "load:bill_url:BILLURL2",
    ]
    assert updates == [("BILLURL1", True), ("BILLURL2", True)]
