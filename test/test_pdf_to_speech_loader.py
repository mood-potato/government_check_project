from pipelines.pdf_to_speech_pipeline import PDFToSpeechLoader


class RecordingPDFToSpeechLoader(PDFToSpeechLoader):
    def __init__(self, select_results=None):
        super().__init__(connection=None)
        self.queries = []
        self.params = []
        self.select_results = select_results or {}

    def _execute_query(self, query, params=None):
        self.queries.append(query)
        self.params.append(params)
        if query.strip().upper().startswith("SELECT"):
            return self.select_results.get(params, [])
        return 1


def test_create_table_does_not_create_legacy_speakers_table():
    loader = RecordingPDFToSpeechLoader()

    loader.create_table()

    executed_sql = "\n".join(loader.queries)
    assert "CREATE TABLE IF NOT EXISTS speakers" not in executed_sql
    assert "ALTER TABLE speakers" not in executed_sql
    assert "speaker_name TEXT" in executed_sql


def test_save_all_data_preserves_non_member_speaker_without_speaker_id():
    member_id = "11111111-1111-1111-1111-111111111111"
    loader = RecordingPDFToSpeechLoader(
        {
            ("국회의원", 22): [(member_id,)],
            ("정부위원", 22): [],
        }
    )

    loader._save_all_data(
        [
            {
                "pdf_url_id": "PDF1",
                "speaker": "국회의원",
                "speaker_title": "의원",
                "date": "2026-01-01",
                "title": "회의",
                "class_name": "본회의",
                "confer_number": 1,
                "dae_number": 22,
                "text": "발언 1",
                "summary": "요약 1",
                "timestamp": "2026-01-01T00:00:00",
            },
            {
                "pdf_url_id": "PDF1",
                "speaker": "정부위원",
                "speaker_title": "장관",
                "date": "2026-01-01",
                "title": "회의",
                "class_name": "본회의",
                "confer_number": 1,
                "dae_number": 22,
                "text": "발언 2",
                "summary": None,
                "timestamp": "2026-01-01T00:00:01",
            },
        ]
    )

    insert_params = [
        params for params in loader.params if params and params[0] == "PDF1"
    ]

    assert insert_params[0][2] == member_id
    assert insert_params[0][3] == "국회의원"
    assert insert_params[1][2] is None
    assert insert_params[1][3] == "정부위원"
