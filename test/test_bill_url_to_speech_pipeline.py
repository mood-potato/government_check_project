from pathlib import Path

from pipelines.pdf_to_speech_pipeline import (
    BillURLToSpeechExtractor,
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
