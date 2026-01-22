import pytest
from datetime import datetime
from unittest.mock import MagicMock


@pytest.fixture
def mock_db_connection():
    """PostgreSQL 연결 모킹"""
    connection = MagicMock()
    cursor = MagicMock()

    # cursor context manager 설정
    connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

    return connection


@pytest.fixture
def sample_schedule_data():
    """샘플 일정 데이터"""
    return [
        {"MEETTING_DATE": "2024-01-15", "TITLE": "제22대 제1회 본회의"},
        {"MEETTING_DATE": "2024-01-16", "TITLE": "제22대 제2회 본회의"},
        {"MEETTING_DATE": "2024-01-15", "TITLE": "제22대 제1회 본회의"},  # 중복
    ]


@pytest.fixture
def sample_pdf_text():
    """샘플 PDF 텍스트 (발언 패턴 포함)"""
    return """
◯의장 홍길동
오늘 회의를 시작하겠습니다. 의사일정 제1항부터 제10항까지는 일괄 상정합니다.
◯위원 김철수
저는 이 안건에 찬성합니다. 국민의 이익을 위해 반드시 통과되어야 합니다.
◯위원 박영희
저는 반대 의견을 제시합니다. 예산 문제에 대한 검토가 더 필요합니다.
"""


@pytest.fixture
def sample_pdf_api_response():
    """PDF URL API 응답 샘플"""
    return [
        {
            "CONF_DATE": "2024-01-15",
            "TITLE": "제22대 제1회 본회의",
            "CONFER_NUM": "1",
            "DAE_NUM": "22",
            "CLASS_NAME": "본회의",
            "SUB_NAME": "의사일정",
            "VOD_LINK_URL": "http://example.com/vod",
            "CONF_LINK_URL": "http://example.com/conf",
            "PDF_LINK_URL": "http://example.com/pdf",
        },
    ]


@pytest.fixture
def sample_speech_data():
    """샘플 발언 데이터"""
    return [
        {
            "pdf_url_id": "test-uuid-001",
            "speaker": "의장 홍길동",
            "text": "오늘 회의를 시작하겠습니다.",
            "date": "2024-01-15",
            "speech_number": 1,
            "class_name": "본회의",
            "confer_number": "1",
            "dae_number": "22",
            "title": "제22대 제1회 본회의",
            "file_path": "http://example.com/pdf",
            "summary": None,
            "timestamp": datetime.now(),
        },
        {
            "pdf_url_id": "test-uuid-001",
            "speaker": "위원 김철수",
            "text": "저는 이 안건에 찬성합니다.",
            "date": "2024-01-15",
            "speech_number": 2,
            "class_name": "본회의",
            "confer_number": "1",
            "dae_number": "22",
            "title": "제22대 제1회 본회의",
            "file_path": "http://example.com/pdf",
            "summary": None,
            "timestamp": datetime.now(),
        },
    ]


@pytest.fixture
def mock_api_schedule_response():
    """Open Assembly 일정 API 응답 모킹"""
    return {
        "nekcaiymatialqlxr": [
            {"head": [{"list_total_count": 2}]},
            {
                "row": [
                    {"MEETTING_DATE": "2024-01-15", "TITLE": "본회의"},
                    {"MEETTING_DATE": "2024-01-16", "TITLE": "상임위원회"},
                ]
            },
        ]
    }


@pytest.fixture
def mock_api_pdf_response():
    """Open Assembly PDF URL API 응답 모킹"""
    return {
        "nzbyfwhwaoanttzje": [
            {"head": [{"list_total_count": 1}]},
            {
                "row": [
                    {
                        "CONF_DATE": "2024-01-15",
                        "TITLE": "제22대 제1회 본회의",
                        "PDF_LINK_URL": "http://test.pdf",
                    }
                ]
            },
        ]
    }
