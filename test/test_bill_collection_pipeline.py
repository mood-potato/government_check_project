from pipelines.bill_collection_pipeline import (
    BillInfoLoader,
    BillInfoTransformer,
    BillUrlLoader,
    BillUrlTransformer,
)
from pipelines.utils.request_utils import request_paginated_data


def test_bill_info_transformer_normalizes_openapi_rows():
    rows = [
        {
            "CONF_ID": "N054211",
            "ERACO": "제22대",
            "SESS": "제434회",
            "DGR": "제2차",
            "BILL_ID": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "BILL_NM": "2. 방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "LINK_URL": "https://likms.assembly.go.kr/bill/billDetail.do?billId=PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
        }
    ]

    transformed = BillInfoTransformer().transform(rows)

    assert transformed == [
        {
            "meeting_id": "N054211",
            "dae_number": 22,
            "session_number": 434,
            "confer_number": 2,
            "bill_id": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "bill_name": "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "bill_order": 2,
            "detail_link": "https://likms.assembly.go.kr/bill/billDetail.do?billId=PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
        }
    ]


def test_bill_url_transformer_normalizes_bill_conference_rows():
    rows = [
        {
            "BILL_ID": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "BILL_NM": "17. 방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "CONF_KND": "상임위원회 회의록",
            "CONF_ID": "N054161",
            "ERACO": "제22대",
            "SESS": "제434회",
            "DGR": "제3차",
            "CONF_DT": "20260409",
            "DOWN_URL": "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=56533",
        }
    ]

    transformed = BillUrlTransformer().transform(rows)

    assert transformed == [
        {
            "agenda_id": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "agenda_name": "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "meeting_type": "상임위원회 회의록",
            "meeting_id": "N054161",
            "dae_number": 22,
            "meeting_date": "2026-04-09",
            "download_url": "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=56533",
            "get_pdf": False,
        }
    ]


def test_bill_info_loader_uses_unique_upsert_key():
    loader = BillInfoLoader(connection=object())
    calls = []
    loader._execute_query = lambda query, params=None: calls.append((query, params))

    loader.load(
        {
            "meeting_id": "N054211",
            "dae_number": 22,
            "session_number": 434,
            "confer_number": 2,
            "bill_id": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "bill_name": "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "bill_order": 2,
            "detail_link": "https://example.com",
        }
    )

    query, params = calls[0]
    assert "INSERT INTO bill_info" in query
    assert "ON CONFLICT (meeting_id, bill_id) DO UPDATE" in query
    assert params == (
        "N054211",
        22,
        434,
        2,
        "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
        "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
        2,
        "https://example.com",
    )


def test_bill_url_loader_uses_unique_upsert_key():
    loader = BillUrlLoader(connection=object())
    calls = []
    loader._execute_query = lambda query, params=None: calls.append((query, params))

    loader.load(
        {
            "agenda_id": "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
            "agenda_name": "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
            "meeting_type": "상임위원회 회의록",
            "meeting_id": "N054161",
            "dae_number": 22,
            "meeting_date": "2026-04-09",
            "download_url": "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=56533",
            "get_pdf": False,
        }
    )

    query, params = calls[0]
    assert "INSERT INTO bill_url" in query
    assert "ON CONFLICT (agenda_id, meeting_id, download_url) DO UPDATE" in query
    assert params == (
        "PRC_V2D6E0C3C0A5C1A1A4P7Q0O8N6N3L2",
        "방송법 일부개정법률안(김현 의원 대표발의)(의안번호 2217305)",
        "상임위원회 회의록",
        "N054161",
        22,
        "2026-04-09",
        "https://record.assembly.go.kr/assembly/viewer/minutes/download/pdf.do?id=56533",
        False,
    )


def test_request_paginated_data_wraps_single_row_objects(monkeypatch):
    class Response:
        request = type("Request", (), {"url": "https://example.com"})()

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "VCONFBILLCONFLIST": [
                    {"head": []},
                    {"row": {"BILL_ID": "PRC_SINGLE"}},
                ]
            }

    monkeypatch.setattr("pipelines.utils.request_utils.requests.get", lambda **kwargs: Response())

    rows = request_paginated_data(
        "https://open.assembly.go.kr/portal/openapi/VCONFBILLCONFLIST",
        {"KEY": "key", "Type": "json"},
        "VCONFBILLCONFLIST",
        page_size=100,
        max_pages=1,
    )

    assert rows == [{"BILL_ID": "PRC_SINGLE"}]
