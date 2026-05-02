from pipelines.bill_collection_pipeline import (
    BillInfoLoader,
    BillInfoTransformer,
    BillUrlWorkbookExtractor,
    BillUrlLoader,
    BillUrlTransformer,
)
from pipelines.base import BasePipeline
from pipelines.utils.openapi import request_paginated_data


class DummyPipeline(BasePipeline):
    """테스트용 파이프라인입니다."""

    def run(self):
        """테스트에서는 실행하지 않습니다."""
        return None


def test_base_loader_logs_with_loader_prefix(monkeypatch):
    messages = []
    loader = BillInfoLoader(connection=object())

    monkeypatch.setattr("pipelines.base.logger.info", messages.append)

    loader.log_info("테이블 준비 완료")

    assert messages == ["[Loader] 테이블 준비 완료"]


def test_base_pipeline_logs_with_pipeline_prefix(monkeypatch):
    messages = []
    pipeline = DummyPipeline(extractor=object(), loader=object())

    monkeypatch.setattr("pipelines.base.logger.info", messages.append)

    pipeline.log_info("실행 시작")

    assert messages == ["[Pipeline] 실행 시작"]


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


def test_bill_url_workbook_extractor_reads_korean_header_xlsx(tmp_path):
    import zipfile

    workbook_path = tmp_path / "bill_url.xlsx"
    worksheet_xml = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>의안 ID</t></is></c>
      <c r="B1" t="inlineStr"><is><t>의안명</t></is></c>
      <c r="C1" t="inlineStr"><is><t>회의 종류</t></is></c>
      <c r="D1" t="inlineStr"><is><t>회의 ID</t></is></c>
      <c r="E1" t="inlineStr"><is><t>대수</t></is></c>
      <c r="F1" t="inlineStr"><is><t>회의일자</t></is></c>
      <c r="G1" t="inlineStr"><is><t>다운URL</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>PRC_SAMPLE</t></is></c>
      <c r="B2" t="inlineStr"><is><t>1. 샘플 법률안</t></is></c>
      <c r="C2" t="inlineStr"><is><t>국회본회의 회의록</t></is></c>
      <c r="D2" t="inlineStr"><is><t>N054223</t></is></c>
      <c r="E2" t="inlineStr"><is><t>제22대</t></is></c>
      <c r="F2" t="inlineStr"><is><t xml:space="preserve">20260423        </t></is></c>
      <c r="G2" t="inlineStr"><is><t>https://example.com/a.pdf</t></is></c>
    </row>
  </sheetData>
</worksheet>
"""
    workbook_xml = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="의안별 회의록 목록" r:id="rId1" sheetId="1"/></sheets>
</workbook>
"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
    with zipfile.ZipFile(workbook_path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    rows = BillUrlWorkbookExtractor(workbook_path).extract()

    assert rows == [
        {
            "BILL_ID": "PRC_SAMPLE",
            "BILL_NM": "1. 샘플 법률안",
            "CONF_KND": "국회본회의 회의록",
            "CONF_ID": "N054223",
            "ERACO": "제22대",
            "CONF_DT": "20260423",
            "DOWN_URL": "https://example.com/a.pdf",
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
    assert "RETURNING id, (xmax = 0) AS inserted;" in query
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
    assert "RETURNING id, (xmax = 0) AS inserted;" in query
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


def test_bill_url_loader_logs_row_event_for_inserted(monkeypatch):
    events = []
    loader = BillUrlLoader(connection=object(), run_id="run-1")
    loader._execute_query = lambda query, params=None: [{"id": "1", "inserted": True}]

    monkeypatch.setattr(
        loader,
        "log_load_row_event",
        lambda **kwargs: events.append(kwargs),
    )

    loader.load(
        {
            "agenda_id": "A1",
            "agenda_name": "의안",
            "meeting_type": "본회의",
            "meeting_id": "M1",
            "dae_number": 22,
            "meeting_date": "2026-04-09",
            "download_url": "https://example.com",
            "get_pdf": False,
        }
    )

    assert events == [
        {
            "target_table": "bill_url",
            "record_key": "A1:M1:https://example.com",
            "action": "inserted",
            "source_date": "2026-04-09",
            "meta": {"agenda_name": "의안", "meeting_type": "본회의"},
        }
    ]


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

    monkeypatch.setattr(
        "pipelines.utils.openapi.requests.get", lambda **kwargs: Response()
    )

    rows = request_paginated_data(
        "https://open.assembly.go.kr/portal/openapi/VCONFBILLCONFLIST",
        {"KEY": "key", "Type": "json"},
        "VCONFBILLCONFLIST",
        page_size=100,
        max_pages=1,
    )

    assert rows == [{"BILL_ID": "PRC_SINGLE"}]


def test_request_paginated_data_uses_conservative_workers_and_timeout(monkeypatch):
    executor_calls = []
    request_calls = []

    class Response:
        request = type("Request", (), {"url": "https://example.com"})()

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "VCONFBILLCONFLIST": [
                    {"head": []},
                    {"row": [{"BILL_ID": "PRC_SINGLE"}]},
                ]
            }

    class ImmediateExecutor:
        def __init__(self, max_workers):
            executor_calls.append(max_workers)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def map(self, func, iterable):
            return [func(item) for item in iterable]

    def fake_get(**kwargs):
        request_calls.append(kwargs)
        return Response()

    monkeypatch.setattr("pipelines.utils.openapi.ThreadPoolExecutor", ImmediateExecutor)
    monkeypatch.setattr("pipelines.utils.openapi.requests.get", fake_get)

    request_paginated_data(
        "https://open.assembly.go.kr/portal/openapi/VCONFBILLCONFLIST",
        {"KEY": "key", "Type": "json"},
        "VCONFBILLCONFLIST",
        page_size=100,
        max_pages=1,
    )

    assert executor_calls == [3]
    assert request_calls[0]["timeout"] == (5, 30)


def test_request_paginated_data_shows_progress_and_batches_requests(monkeypatch):
    requested_pages = []
    progress_calls = []

    class Response:
        request = type("Request", (), {"url": "https://example.com"})()

        def __init__(self, page):
            self.page = page

        def raise_for_status(self):
            return None

        def json(self):
            if self.page == 2:
                return {"RESULT": {"MESSAGE": "해당하는 데이터가 없습니다."}}
            return {
                "VCONFBILLCONFLIST": [
                    {"head": []},
                    {"row": [{"BILL_ID": f"PRC_{self.page}"}]},
                ]
            }

    class Progress:
        def __init__(self, *args, **kwargs):
            progress_calls.append(("init", kwargs))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def update(self, count):
            progress_calls.append(("update", count))

    def fake_get(**kwargs):
        page = int(kwargs["params"]["pIndex"])
        requested_pages.append(page)
        return Response(page)

    monkeypatch.setattr("pipelines.utils.openapi.requests.get", fake_get)
    monkeypatch.setattr("pipelines.utils.openapi.tqdm", Progress)

    rows = request_paginated_data(
        "https://open.assembly.go.kr/portal/openapi/VCONFBILLCONFLIST",
        {"KEY": "key", "Type": "json"},
        "VCONFBILLCONFLIST",
        page_size=100,
        max_pages=10,
        max_workers=3,
    )

    assert rows == [{"BILL_ID": "PRC_1"}]
    assert sorted(requested_pages) == [1, 2, 3]
    assert progress_calls[0] == (
        "init",
        {
            "total": 10,
            "desc": "VCONFBILLCONFLIST 페이지 수집",
            "unit": "page",
            "leave": False,
            "disable": False,
        },
    )
    assert progress_calls.count(("update", 1)) == 2
