from backend.api.services.home_service import HomeService


def test_home_service_maps_speakers_to_featured_members(monkeypatch):
    rows = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "mona_code": "ABC123",
            "assembly_number": 22,
            "name": "강테스트",
            "political_party": "테스트당",
            "election_district": "서울 테스트구",
            "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "mona_code": "XYZ789",
            "assembly_number": 21,
            "name": "비례테스트",
            "political_party": "예시당",
            "election_district": None,
            "profile_image_url": None,
        },
    ]
    calls = []

    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_all",
        lambda query, params=(): calls.append((query, params)) or rows,
    )

    featured_members = HomeService.get_featured_members()

    assert "FROM speakers sp" in calls[0][0]
    assert "GROUP BY speaker_id" not in calls[0][0]
    assert "COUNT(*) AS speech_count" not in calls[0][0]
    assert "MAX(date) AS latest_speech_date" not in calls[0][0]
    assert "LEFT JOIN (" not in calls[0][0]
    assert "ORDER BY sp.name ASC" in calls[0][0]
    assert featured_members == [
        {
            "rank": 1,
            "member": {
                "id": "11111111-1111-1111-1111-111111111111",
                "slug": "abc123-22",
                "name": "강테스트",
                "party_name": "테스트당",
                "district_name": "서울 테스트구",
                "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
            },
            "summary": "22대 테스트당 서울 테스트구",
        },
        {
            "rank": 2,
            "member": {
                "id": "22222222-2222-2222-2222-222222222222",
                "slug": "xyz789-21",
                "name": "비례테스트",
                "party_name": "예시당",
                "district_name": None,
                "profile_image_url": None,
            },
            "summary": "21대 예시당",
        },
    ]


def test_home_service_returns_empty_featured_members_when_no_speakers(monkeypatch):
    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_all",
        lambda query, params=(): [],
    )

    featured_members = HomeService.get_featured_members()

    assert featured_members == []


def test_home_service_returns_hero_snapshot_payload(monkeypatch):
    payload = {
        "member": {
            "id": "11111111-1111-1111-1111-111111111111",
            "slug": "abc123-22",
            "name": "강테스트",
            "party_name": "테스트당",
            "district_name": "서울 테스트구",
            "profile_image_url": None,
        },
        "topic_label": "예산",
        "topic_slug": "budget",
        "past_speech": {
            "spoken_date": "2024-01-01",
            "meeting_name": "본회의",
            "speech_text": "과거 발언",
            "original_url": None,
        },
        "recent_speech": {
            "spoken_date": "2026-01-01",
            "meeting_name": "본회의",
            "speech_text": "최근 발언",
            "original_url": None,
        },
        "summary": "예산 관련 발언을 비교했습니다.",
    }
    calls = []

    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_one",
        lambda query, params=(): calls.append((query, params)) or {"payload": payload},
    )

    assert HomeService.get_home_hero() == payload
    assert "home_section_snapshot" in calls[0][0]
    assert calls[0][1] == ("hero",)


def test_home_service_returns_empty_hero_when_snapshot_missing(monkeypatch):
    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_one",
        lambda query, params=(): None,
    )

    assert HomeService.get_home_hero() is None
