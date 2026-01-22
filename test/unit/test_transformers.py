import pytest
from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
from modules.transform.congress_schedule_transformer import CongressScheduleTransformer


class TestPDFToSpeechTransformer:
    def test_transform_extracts_speakers(self, sample_pdf_text):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="test-uuid",
            text=sample_pdf_text,
            title="테스트 회의",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        assert len(result) == 3
        assert result[0]["speaker"] == "의장 홍길동"
        assert result[1]["speaker"] == "위원 김철수"
        assert result[2]["speaker"] == "위원 박영희"

    def test_transform_preserves_speech_content(self, sample_pdf_text):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="test-uuid",
            text=sample_pdf_text,
            title="테스트",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        assert "회의를 시작하겠습니다" in result[0]["text"]
        assert "찬성합니다" in result[1]["text"]
        assert "반대 의견" in result[2]["text"]

    def test_transform_assigns_correct_speech_numbers(self, sample_pdf_text):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="test-uuid",
            text=sample_pdf_text,
            title="테스트",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        assert result[0]["speech_number"] == 1
        assert result[1]["speech_number"] == 2
        assert result[2]["speech_number"] == 3

    def test_transform_empty_text_returns_empty_list(self):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="test",
            text="",
            title="",
            date="",
            confer_number="",
            dae_number="",
            class_name="",
            file_path="",
        )

        assert result == []

    def test_transform_text_without_speakers_returns_empty_list(self):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="test",
            text="이것은 발언자 패턴이 없는 텍스트입니다.",
            title="테스트",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        assert result == []

    def test_transform_includes_metadata(self, sample_pdf_text):
        transformer = PDFToSpeechTransformer()

        result = transformer.transform(
            pdf_url_id="uuid-123",
            text=sample_pdf_text,
            title="제22대 본회의",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://example.com/pdf",
        )

        speech = result[0]
        assert speech["pdf_url_id"] == "uuid-123"
        assert speech["title"] == "제22대 본회의"
        assert speech["date"] == "2024-01-15"
        assert speech["confer_number"] == "1"
        assert speech["dae_number"] == "22"
        assert speech["class_name"] == "본회의"
        assert speech["file_path"] == "http://example.com/pdf"
        assert speech["summary"] is None
        assert "timestamp" in speech


class TestCongressScheduleTransformer:
    def test_transform_extracts_unique_dates(self, sample_schedule_data):
        transformer = CongressScheduleTransformer()

        result = transformer.transform(sample_schedule_data)

        assert len(result) == 2  # 중복 제거됨
        assert "2024-01-15" in result
        assert "2024-01-16" in result

    def test_transform_returns_sorted_dates(self, sample_schedule_data):
        transformer = CongressScheduleTransformer()

        result = transformer.transform(sample_schedule_data)

        assert result == sorted(result)

    def test_transform_empty_data_returns_empty_list(self):
        transformer = CongressScheduleTransformer()

        result = transformer.transform([])

        assert result == []

    def test_transform_single_date(self):
        transformer = CongressScheduleTransformer()
        data = [{"MEETTING_DATE": "2024-03-01", "TITLE": "회의"}]

        result = transformer.transform(data)

        assert result == ["2024-03-01"]
