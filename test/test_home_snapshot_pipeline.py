import json
from pathlib import Path

from pipelines.home_snapshot_pipeline import HomeHeroSnapshotExtractor, HomeSnapshotLoader


class FakeCursor:
    def __init__(self, fetchone_result=None):
        self.executed = []
        self.fetchone_result = fetchone_result

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, fetchone_result=None):
        self.cursor_instance = FakeCursor(fetchone_result=fetchone_result)
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


def test_home_snapshot_loader_creates_snapshot_table():
    connection = FakeConnection()
    loader = HomeSnapshotLoader(connection)

    loader.create_table()

    query, params = connection.cursor_instance.executed[0]
    assert params is None
    assert "CREATE TABLE IF NOT EXISTS home_section_snapshot" in query
    assert "payload          jsonb NOT NULL" in query
    assert "version          integer NOT NULL DEFAULT 1" in query
    assert connection.commits == 1


def test_home_snapshot_loader_upserts_hero_payload():
    connection = FakeConnection()
    loader = HomeSnapshotLoader(connection)
    payload = {"hero": {"summary": "최근 상반 발언 후보"}}

    loader.load("hero", payload, ttl_minutes=10)

    query, params = connection.cursor_instance.executed[0]
    assert "ON CONFLICT (section_key)" in query
    assert "version = home_section_snapshot.version + 1" in query
    assert params[0] == "hero"
    assert json.loads(params[1]) == payload
    assert params[2] == 10
    assert connection.commits == 1


def test_home_hero_snapshot_extractor_builds_payload_from_recent_speaker():
    connection = FakeConnection(
        fetchone_result=(
            "11111111-1111-1111-1111-111111111111",
            "abc123",
            22,
            "강테스트",
            "테스트당",
            "서울 테스트구",
            "https://example.com/profile.jpg",
            "예산결산특별위원회",
            "2026-05-01",
            "최근 발언입니다.",
            "https://example.com/recent",
            "2024-01-01",
            "과거 발언입니다.",
            "https://example.com/past",
        )
    )

    payload = HomeHeroSnapshotExtractor(connection=connection).extract()

    query, params = connection.cursor_instance.executed[0]
    assert "FROM speeches recent" in query
    assert "JOIN speakers sp" in query
    assert "JOIN LATERAL" in query
    assert params == (160, 160, 22)
    assert payload == {
        "member": {
            "id": "11111111-1111-1111-1111-111111111111",
            "slug": "abc123-22",
            "name": "강테스트",
            "party_name": "테스트당",
            "district_name": "서울 테스트구",
            "profile_image_url": "https://example.com/profile.jpg",
        },
        "topic_label": "예산결산특별위원회",
        "topic_slug": None,
        "past_speech": {
            "spoken_date": "2024-01-01",
            "meeting_name": "예산결산특별위원회",
            "speech_text": "과거 발언입니다.",
            "original_url": "https://example.com/past",
        },
        "recent_speech": {
            "spoken_date": "2026-05-01",
            "meeting_name": "예산결산특별위원회",
            "speech_text": "최근 발언입니다.",
            "original_url": "https://example.com/recent",
        },
        "summary": "강테스트 의원의 최근 발언과 과거 발언을 함께 확인할 수 있는 비교 후보입니다.",
    }


def test_schema_has_indexes_for_home_hero_snapshot_query():
    schema = Path("schema.sql").read_text(encoding="utf-8")

    assert "idx_speeches_recent_member" in schema
    assert "idx_speeches_speaker_date_order" in schema
