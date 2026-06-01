import pathlib

import pdfplumber

from pipelines.pdf_to_speech_pipeline import PDFToSpeechTransformer


def _transform_text(text):
    return PDFToSpeechTransformer().transform(
        pdf_url_id="LOCAL",
        text=text,
        title="제434회 법제사법위원회",
        date="2026-04-22",
        confer_number=3,
        dae_number=22,
        class_name="법제사법위원회",
        file_path="local.pdf",
    )


def test_transform_removes_page_headers_from_speech_text():
    text = """
◯박은정 위원 그러면 쿠팡 같은 경우에 작년 11월에 개인정보 유출 피해가 발생했습니다.
32 제434회-법제사법제3차(2026년4월22일)
전적 규제가 없는데 우리는 사전적 규제가 있다.
◯진술인 한경수 예, 그렇습니다.
"""

    speeches = _transform_text(text)

    assert speeches[0]["speaker"] == "박은정"
    assert "쿠팡 같은 경우" in speeches[0]["text"]
    assert "제434회-법제사법제3차" not in speeches[0]["text"]
    assert speeches[1]["speaker"] == "한경수"


def test_transform_removes_separator_lines_from_speech_text():
    text = """
◯김기표 위원 같이 마이크를 주세요, 저도 얘기하게.
…………………………………………………………………………………………………………
◯위원장 서영교 다른 분의 시간을 조금 보시고요.
"""

    speeches = _transform_text(text)

    assert speeches[0]["speaker"] == "김기표"
    assert "마이크를 주세요" in speeches[0]["text"]
    assert "…" not in speeches[0]["text"]


def test_transform_drops_agenda_list_between_speeches():
    text = """
◯위원장 서영교 잠시 정회하도록 하겠습니다.
98. 공동주택관리법 일부개정법률안(권영진 의원 대표발의)(의안번호 2210409)
99. 공항경제권 개발 및 지원에 관한 특별법안(배준영 의원 대표발의)(의안번호 2200233)
100. 공항시설법 일부개정법률안(맹성규 의원 대표발의)(의안번호 2213840)
◯위원장 서영교 다음으로 국토교통위원회 소관 의사일정 98항부터 107항까지 상정합니다.
"""

    speeches = _transform_text(text)

    assert len(speeches) == 2
    assert "공동주택관리법" not in speeches[0]["text"]
    assert speeches[1]["text"].startswith("다음으로 국토교통위원회")


def test_transform_ignores_attendance_appendix():
    text = """
◯위원장 서영교 산회를 선포합니다.
(20시19분 산회)
◯출석 위원(18인)
곽규택 김기표 김동아 김용민 김재섭 나경원 박균택 박은정
◯출석 전문위원
수석전문위원 심정희
"""

    speeches = _transform_text(text)

    assert len(speeches) == 1
    assert speeches[0]["speaker"] == "서영교"
    assert "출석 위원" not in speeches[0]["text"]


def test_transform_extracts_expected_chunks_from_local_pdf():
    pdf_path = next(pathlib.Path("data").glob("*.pdf"))
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    speeches = PDFToSpeechTransformer().transform(
        pdf_url_id="LOCAL",
        text=text,
        title=pdf_path.name,
        date="2026-04-22",
        confer_number=3,
        dae_number=22,
        class_name="법제사법위원회",
        file_path=str(pdf_path),
    )

    assert len(speeches) < 1316
    assert not any(speech["speaker"] == "출석 위원" for speech in speeches)
    assert not any("출석 전문위원" in speech["text"] for speech in speeches)

    park_speech = next(
        speech for speech in speeches if "쿠팡 같은 경우" in speech["text"]
    )
    assert park_speech["speaker"] == "박은정"
    assert "제434회-법제사법제3차" not in park_speech["text"]

    kim_speech = next(
        speech for speech in speeches if "같이 마이크를 주세요" in speech["text"]
    )
    assert kim_speech["speaker"] == "김기표"
    assert "…" not in kim_speech["text"]
