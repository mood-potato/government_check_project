from datetime import date

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
            "latest_speech_date": date(2026, 5, 1),
            "speech_count": 3,
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "mona_code": "XYZ789",
            "assembly_number": 21,
            "name": "비례테스트",
            "political_party": "예시당",
            "election_district": None,
            "profile_image_url": None,
            "latest_speech_date": None,
            "speech_count": 0,
        },
    ]
    calls = []

    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_all",
        lambda query, params=(): calls.append((query, params)) or rows,
    )

    home = HomeService.get_home()

    assert "LEFT JOIN (" in calls[0][0]
    assert "MAX(date) AS latest_speech_date" in calls[0][0]
    assert "ORDER BY recent_speeches.latest_speech_date DESC NULLS LAST" in calls[0][0]
    assert home["hero"] is None
    assert home["popular_keywords"] == []
    assert home["recent_cases"] == []
    assert home["featured_members"] == [
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
            "summary": "최근 발언 2026.05.01 · 3건",
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
    assert (
        home["disclaimer"]
        == "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
    )


def test_home_service_returns_empty_featured_members_when_no_speakers(monkeypatch):
    monkeypatch.setattr(
        "backend.api.services.home_service.Database.fetch_all",
        lambda query, params=(): [],
    )

    home = HomeService.get_home()

    assert home["hero"] is None
    assert home["featured_members"] == []
