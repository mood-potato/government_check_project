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
        assert result[0]["speaker"] == "홍길동"
        assert result[0]["speaker_title"] == "의장"
        assert result[1]["speaker"] == "김철수"
        assert result[1]["speaker_title"] == "위원"
        assert result[2]["speaker"] == "박영희"
        assert result[2]["speaker_title"] == "위원"

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


class TestPDFToSpeechPreprocessing:
    def test_preprocess_removes_page_headers(self):
        transformer = PDFToSpeechTransformer()
        text = "제431회-제1차(2026년1월15일) 3\n◯의장 홍길동\n회의를 시작합니다."
        result = transformer._preprocess_text(text)
        assert "제431회-제1차" not in result
        assert "◯의장 홍길동" in result

    def test_preprocess_removes_appendix(self):
        transformer = PDFToSpeechTransformer()
        text = "◯의장 홍길동\n회의 발언\n◯출석 의원\n부록 내용"
        result = transformer._preprocess_text(text)
        assert "부록 내용" not in result
        assert "회의 발언" in result

    def test_preprocess_removes_earliest_appendix_marker(self):
        # 회귀 테스트: 리스트 순서가 아닌 텍스트에서 먼저 나타나는 마커 기준으로 잘라야 함
        # "◯산회 선포"가 "◯출석 의원"보다 텍스트에서 먼저 나타나지만
        # APPENDIX_MARKERS 리스트에서는 "◯출석 의원"이 앞에 있음
        transformer = PDFToSpeechTransformer()
        text = "◯의장 홍길동\n발언 내용\n◯산회 선포\n(14시50분)\n◯출석 의원\n김철수 박영희"
        result = transformer._preprocess_text(text)
        assert "발언 내용" in result
        assert "◯산회 선포" not in result
        assert "◯출석 의원" not in result
        assert "김철수 박영희" not in result

    def test_clean_speech_removes_timestamps(self):
        transformer = PDFToSpeechTransformer()
        text = "(14시41분 개의)\n성원이 되었으므로 회의를 시작하겠습니다."
        result = transformer._clean_speech_text(text)
        assert "14시41분" not in result
        assert "회의를 시작하겠습니다" in result

    def test_clean_speech_removes_stage_directions(self):
        transformer = PDFToSpeechTransformer()
        text = "의원 선서를 하겠습니다.\n(일동 기립)\n(전자투표)"
        result = transformer._clean_speech_text(text)
        assert "일동 기립" not in result
        assert "전자투표" not in result
        assert "의원 선서를 하겠습니다" in result

    def test_clean_speech_removes_agenda_markers(self):
        transformer = PDFToSpeechTransformer()
        text = "발언 내용입니다.\no 의원(이소희) 선서 및 인사\n다음 발언입니다."
        result = transformer._clean_speech_text(text)
        assert "o 의원(이소희)" not in result
        assert "발언 내용입니다" in result

    def test_clean_speech_removes_procedural_memo(self):
        transformer = PDFToSpeechTransformer()
        text = "의안을 상정합니다.\n(대안은 부록으로 보존함)"
        result = transformer._clean_speech_text(text)
        assert "부록으로 보존함" not in result
        assert "의안을 상정합니다" in result


class TestNonSpeechFiltering:
    def test_regex_ignores_non_speech_markers(self, sample_pdf_text_with_false_positives):
        transformer = PDFToSpeechTransformer()
        result = transformer.transform(
            pdf_url_id="test",
            text=sample_pdf_text_with_false_positives,
            title="테스트",
            date="2024-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        speakers = [s["speaker"] for s in result]
        assert "우원식" in speakers
        assert "김철수" in speakers
        assert len(result) == 2  # 의안명, 의안 심사 제외

    def test_filters_law_amendment_names(self):
        transformer = PDFToSpeechTransformer()
        assert transformer._is_non_speech("군인사법 일부개정법률안") is True
        assert transformer._is_non_speech("농어촌특별세법 일부개정법률안") is True

    def test_filters_appendix_metadata(self):
        transformer = PDFToSpeechTransformer()
        assert transformer._is_non_speech("출석 의원") is True
        assert transformer._is_non_speech("의안 심사") is True
        assert transformer._is_non_speech("보고서 제출") is True

    def test_does_not_filter_real_speakers(self):
        transformer = PDFToSpeechTransformer()
        assert transformer._is_non_speech("의장 우원식") is False
        assert transformer._is_non_speech("이소희 의원") is False
        assert transformer._is_non_speech("위원 김철수") is False

    def test_filters_law_name_split_across_speaker_and_speech(self):
        """◯노후계획도시 정비 및 지원에 관한 특별법 일부개정법률안 패턴"""
        transformer = PDFToSpeechTransformer()
        full_context = "노후계획도시 정비 및 지원에 관한 특별법 일부개정법률안"
        assert transformer._is_non_speech(full_context) is True

    def test_filters_miryeongji_law(self):
        transformer = PDFToSpeechTransformer()
        full_context = "미세먼지 저감 및 관리에 관한 특별법 일부개정법률안"
        assert transformer._is_non_speech(full_context) is True

    def test_filters_capital_market_law(self):
        transformer = PDFToSpeechTransformer()
        full_context = "자본시장과 금융투자업에 관한 법률 일부개정법률안"
        assert transformer._is_non_speech(full_context) is True

    def test_filters_disaster_law(self):
        transformer = PDFToSpeechTransformer()
        full_context = "재난 및 안전관리 기본법 일부개정법률안"
        assert transformer._is_non_speech(full_context) is True

    def test_filters_telecom_fraud_law(self):
        transformer = PDFToSpeechTransformer()
        full_context = "전기통신금융사기 피해 방지 및 피해금 환급에 관한 특별법 일부개정법률안"
        assert transformer._is_non_speech(full_context) is True

    def test_transform_excludes_entries_with_no_title_and_law_name_pattern(self):
        """법률 이름이 speaker로 파싱된 경우 transform 결과에서 제외"""
        transformer = PDFToSpeechTransformer()
        text = (
            "◯의장 우원식\n회의를 시작합니다.\n"
            "◯노후계획도시 정비\n및 지원에 관한 특별법 일부개정법률안(대안)\n"
            "◯이소희 의원\n찬성합니다.\n"
        )
        result = transformer.transform(
            pdf_url_id="test", text=text, title="테스트",
            date="2026-01-15", confer_number="1", dae_number="22",
            class_name="본회의", file_path="test.pdf",
        )
        speakers = [s["speaker"] for s in result]
        assert "정비" not in speakers
        assert "우원식" in speakers
        assert "이소희" in speakers
        assert len(result) == 2


class TestSpeakerParsing:
    def test_parse_speaker_title_name(self):
        transformer = PDFToSpeechTransformer()
        title, name = transformer._parse_speaker("의장 우원식")
        assert title == "의장"
        assert name == "우원식"

    def test_parse_speaker_name_title(self):
        transformer = PDFToSpeechTransformer()
        title, name = transformer._parse_speaker("이소희 의원")
        assert title == "의원"
        assert name == "이소희"

    def test_parse_speaker_committee_chair(self):
        transformer = PDFToSpeechTransformer()
        title, name = transformer._parse_speaker("법사위원장 정청래")
        assert title == "법사위원장"
        assert name == "정청래"

    def test_parse_speaker_no_title(self):
        transformer = PDFToSpeechTransformer()
        title, name = transformer._parse_speaker("홍길동")
        assert title is None
        assert name == "홍길동"

    def test_parse_speaker_bureau_chief(self):
        transformer = PDFToSpeechTransformer()
        title, name = transformer._parse_speaker("의사국장 임근원")
        assert title == "의사국장"
        assert name == "임근원"


class TestFullTransformWithNoise:
    def test_transform_with_noise_removes_appendix(self, sample_pdf_text_with_noise):
        transformer = PDFToSpeechTransformer()
        result = transformer.transform(
            pdf_url_id="test",
            text=sample_pdf_text_with_noise,
            title="테스트",
            date="2026-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        speakers = [s["speaker"] for s in result]
        # 부록 이후 내용은 제거됨
        assert "출석 의원" not in [s.get("speaker_raw") for s in result]
        # 실제 발언자만 남음
        assert "우원식" in speakers
        assert "이소희" in speakers
        assert "임근원" in speakers

    def test_transform_with_noise_cleans_text(self, sample_pdf_text_with_noise):
        transformer = PDFToSpeechTransformer()
        result = transformer.transform(
            pdf_url_id="test",
            text=sample_pdf_text_with_noise,
            title="테스트",
            date="2026-01-15",
            confer_number="1",
            dae_number="22",
            class_name="본회의",
            file_path="http://test.pdf",
        )

        first_speech_text = result[0]["text"]
        assert "14시41분" not in first_speech_text
        assert "일동 기립" not in first_speech_text
        assert "제431회-제1차" not in first_speech_text


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
