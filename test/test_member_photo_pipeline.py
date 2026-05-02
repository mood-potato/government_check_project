import pytest

from pipelines.member_photo_pipeline import (
    MemberPhotoExtractor,
    MemberPhotoLoader,
    MemberPhotoTransformer,
)


class FakeCursor:
    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params=None):
        self.queries.append((query, params))


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.commit_count = 0
        self.rollback_count = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1


def test_member_photo_transformer_maps_openapi_rows():
    transformer = MemberPhotoTransformer()

    photos = transformer.transform(
        [
            {
                "NAAS_CD": "ABC123",
                "NAAS_NM": "테스트",
                "NAAS_PIC": "https://open.assembly.go.kr/photo.jpg",
            },
            {
                "NAAS_CD": "EMPTY",
                "NAAS_NM": "사진없음",
                "NAAS_PIC": "",
            },
        ]
    )

    assert photos == [
        {
            "mona_code": "ABC123",
            "name": "테스트",
            "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
            "profile_image_source": "open.assembly.go.kr ALLNAMEMBER",
            "profile_image_license": "공공데이터포털 이용허락범위 제한 없음",
        }
    ]


def test_member_photo_extractor_raises_when_api_returns_no_rows(monkeypatch):
    calls = []

    def fake_request_paginated_data(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    monkeypatch.setattr(
        "pipelines.member_photo_pipeline.request_paginated_data",
        fake_request_paginated_data,
    )
    extractor = MemberPhotoExtractor(
        api_key="test-key",
        page_size=50,
        max_pages=2,
        max_workers=1,
        request_timeout=(15, 60),
    )

    with pytest.raises(RuntimeError, match="ALLNAMEMBER"):
        extractor.extract()

    assert calls[0][1]["page_size"] == 50
    assert calls[0][1]["max_pages"] == 2
    assert calls[0][1]["max_workers"] == 1
    assert calls[0][1]["request_timeout"] == (15, 60)


def test_member_photo_loader_updates_speakers_by_mona_code_and_assembly():
    connection = FakeConnection()
    loader = MemberPhotoLoader(connection, assembly_number=22)
    photo = {
        "mona_code": "ABC123",
        "name": "테스트",
        "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
        "profile_image_source": "open.assembly.go.kr ALLNAMEMBER",
        "profile_image_license": "공공데이터포털 이용허락범위 제한 없음",
    }

    count = loader.load([photo])

    assert count == 1
    assert connection.commit_count == 1
    query, params = connection.cursor_instance.queries[-1]
    assert "UPDATE speakers" in query
    assert "profile_image_url = %s" in query
    assert params == (
        "https://open.assembly.go.kr/photo.jpg",
        "open.assembly.go.kr ALLNAMEMBER",
        "공공데이터포털 이용허락범위 제한 없음",
        "ABC123",
        22,
    )
