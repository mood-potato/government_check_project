from pipelines.schedule_to_pdf_pipeline import PDFUrlLoader, PDFUrlTransformer


def test_pdf_url_transformer_filters_existing_pdf_urls():
    transformer = PDFUrlTransformer(existing_pdf_urls={"https://example.com/old.pdf"})

    transformed = transformer.transform(
        [
            {
                "CONF_DATE": "2026-04-24",
                "TITLE": "제1차 회의",
                "CONFER_NUM": "1",
                "DAE_NUM": "22",
                "CLASS_NAME": "본회의",
                "SUB_NAME": "기존 PDF",
                "VOD_LINK_URL": "https://example.com/vod",
                "CONF_LINK_URL": "https://example.com/conf",
                "PDF_LINK_URL": "https://example.com/old.pdf",
            },
            {
                "CONF_DATE": "2026-04-24",
                "TITLE": "제2차 회의",
                "CONFER_NUM": "2",
                "DAE_NUM": "22",
                "CLASS_NAME": "본회의",
                "SUB_NAME": "신규 PDF",
                "VOD_LINK_URL": "https://example.com/vod",
                "CONF_LINK_URL": "https://example.com/conf",
                "PDF_LINK_URL": "https://example.com/new.pdf",
            },
        ]
    )

    assert [row["PDF_LINK_URL"] for row in transformed] == ["https://example.com/new.pdf"]


def test_pdf_url_loader_logs_row_event_for_inserted(monkeypatch):
    events = []
    loader = PDFUrlLoader(connection=object(), run_id="run-2")
    loader._execute_query = lambda query, params=None: [{"pdf_url_id": "x"}]

    monkeypatch.setattr(
        loader,
        "log_load_row_event",
        lambda **kwargs: events.append(kwargs),
    )

    loader.load(
        {
            "CONFER_NUM": 1,
            "DAE_NUM": 22,
            "CONF_DATE": "2026-04-24",
            "TITLE": "제1차 회의",
            "CLASS_NAME": "본회의",
            "SUB_NAME": "소위원회",
            "VOD_LINK_URL": "https://vod.example.com",
            "CONF_LINK_URL": "https://conf.example.com",
            "PDF_LINK_URL": "https://pdf.example.com/a.pdf",
            "get_pdf": False,
        }
    )

    assert events == [
        {
            "target_table": "pdf_url",
            "record_key": "2026-04-24:제1차 회의:https://pdf.example.com/a.pdf",
            "action": "inserted",
            "source_date": "2026-04-24",
            "meta": {"class_name": "본회의", "confer_number": 1},
        }
    ]
