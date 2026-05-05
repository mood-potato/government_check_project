from backend.api.services.member_service import MemberService


def test_member_service_maps_all_speakers_to_profile_items(monkeypatch):
    calls = []
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
            "assembly_number": 18,
            "name": "비례테스트",
            "political_party": "예시당",
            "election_district": None,
            "profile_image_url": None,
        },
    ]

    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_all",
        lambda query, params=(): calls.append((query, params)) or rows,
    )

    members = MemberService.get_members()

    assert "ORDER BY assembly_number DESC, name ASC" in calls[0][0]
    assert members["items"] == [
        {
            "summary": "22대 테스트당 서울 테스트구",
            "member": {
                "id": "11111111-1111-1111-1111-111111111111",
                "slug": "abc123-22",
                "name": "강테스트",
                "party_name": "테스트당",
                "district_name": "서울 테스트구",
                "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
            },
        },
        {
            "summary": "18대 예시당",
            "member": {
                "id": "22222222-2222-2222-2222-222222222222",
                "slug": "xyz789-18",
                "name": "비례테스트",
                "party_name": "예시당",
                "district_name": None,
                "profile_image_url": None,
            },
        },
    ]


def test_member_service_get_detail_by_slug(monkeypatch):
    calls = []

    def fake_fetch_one(query, params=()):
        calls.append((query, params))
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "mona_code": "ABC123",
            "assembly_number": 22,
            "name": "강테스트",
            "political_party": "테스트당",
            "election_district": "서울 테스트구",
            "election_type": "지역구",
            "reelection_count": 2,
            "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
        }

    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        fake_fetch_one,
    )

    detail = MemberService.get_member_detail("abc123-22")

    assert calls[0][1] == ("ABC123", 22)
    assert detail["member"] == {
        "id": "11111111-1111-1111-1111-111111111111",
        "slug": "abc123-22",
        "name": "강테스트",
        "party_name": "테스트당",
        "district_name": "서울 테스트구",
        "profile_image_url": "https://open.assembly.go.kr/photo.jpg",
        "generation_label": "제22대 국회의원",
        "committee_name": None,
        "status_label": "지역구",
        "fact_summary": "22대 테스트당 서울 테스트구 재선 의원",
    }
    assert detail["metrics"][0] == {"label": "대수", "value": "22대", "tone": "primary"}
    assert detail["conflicts"] == []
    assert detail["agendas"] == []
    assert detail["similar_members"] == []
    assert detail["opposing_members"] == []


def test_member_service_returns_none_for_unknown_slug(monkeypatch):
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        lambda query, params=(): None,
    )

    assert MemberService.get_member_detail("missing-22") is None
    assert MemberService.get_member_detail("bad-slug") is None
