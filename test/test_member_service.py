from datetime import date

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
        if "COUNT(*)" in query:
            return {
                "total_speeches": 0,
                "total_meetings": 0,
                "latest_speech_date": None,
            }
        if "contradiction_candidates" in query:
            return None
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
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_all",
        lambda query, params=(): [],
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
    assert detail["metrics"] == [
        {"label": "총 발언 수", "value": "0", "supporting_text": "건", "tone": "primary"},
        {"label": "참여 회의 수", "value": "0", "supporting_text": "회"},
        {"label": "최근 발언일", "value": "기록 없음"},
        {"label": "대수", "value": "22대"},
    ]
    assert detail["conflicts"] == []
    assert detail["agendas"] == []
    assert detail["similar_members"] == []
    assert detail["opposing_members"] == []
    assert detail["recent_speeches"] == []
    assert detail["contradictory_speeches"] == [
        {"label": "과거 발언", "speech_text": "아직 비교 가능한 발언 후보가 준비되지 않았습니다.", "source": "자동 분석 준비 중", "tone": "past"},
        {"label": "최근 발언", "speech_text": "원문 발언 분석이 완료되면 이 영역에 표시됩니다.", "source": "자동 분석 준비 중", "tone": "recent"},
    ]
    assert detail["contradiction_summary"] is None


def test_member_service_maps_activity_metrics_and_recent_speeches(monkeypatch):
    def fake_fetch_one(query, params=()):
        if "FROM speakers" in query:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "mona_code": "ABC123",
                "assembly_number": 22,
                "name": "강테스트",
                "political_party": "테스트당",
                "election_district": "서울 테스트구",
                "election_type": "지역구",
                "reelection_count": 2,
                "profile_image_url": None,
            }
        if "contradiction_candidates" in query:
            return None
        assert "COUNT(*)" in query
        assert params == ("11111111-1111-1111-1111-111111111111",)
        return {
            "total_speeches": 17,
            "total_meetings": 4,
            "latest_speech_date": "2026-04-24",
        }

    def fake_fetch_all(query, params=()):
        assert "ORDER BY s.date DESC, s.speech_number DESC" in query
        assert "LEFT JOIN bill_url" in query
        assert "s.title" not in query
        assert "\n                    title," not in query
        assert params == ("11111111-1111-1111-1111-111111111111", 5)
        return [
            {
                "id": "speech-2",
                "spoken_date": date(2026, 4, 24),
                "meeting_name": "제2차 본회의",
                "speech_text": "최근 발언 원문입니다.",
                "original_url": "https://record.assembly.go.kr/conf/2",
            },
            {
                "id": "speech-1",
                "spoken_date": "2026-04-21",
                "meeting_name": "제1차 본회의",
                "speech_text": "이전 발언 원문입니다.",
                "original_url": None,
            },
        ]

    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        fake_fetch_one,
    )
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_all",
        fake_fetch_all,
    )

    detail = MemberService.get_member_detail("abc123-22")

    assert detail["metrics"] == [
        {"label": "총 발언 수", "value": "17", "supporting_text": "건", "tone": "primary"},
        {"label": "참여 회의 수", "value": "4", "supporting_text": "회"},
        {"label": "최근 발언일", "value": "2026.04.24"},
        {"label": "대수", "value": "22대"},
    ]
    assert detail["recent_speeches"] == [
        {
            "id": "speech-2",
            "spoken_date": "2026-04-24",
            "meeting_name": "제2차 본회의",
            "speech_text": "최근 발언 원문입니다.",
            "original_url": "https://record.assembly.go.kr/conf/2",
        },
        {
            "id": "speech-1",
            "spoken_date": "2026-04-21",
            "meeting_name": "제1차 본회의",
            "speech_text": "이전 발언 원문입니다.",
            "original_url": None,
        },
    ]


def test_member_service_returns_none_for_unknown_slug(monkeypatch):
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        lambda query, params=(): None,
    )

    assert MemberService.get_member_detail("missing-22") is None
    assert MemberService.get_member_detail("bad-slug") is None


def test_member_service_returns_placeholder_when_no_contradiction_candidate(monkeypatch):
    def fake_fetch_one(query, params=()):
        if "COUNT(*)" in query:
            return {
                "total_speeches": 0,
                "total_meetings": 0,
                "latest_speech_date": None,
            }
        if "contradiction_candidates" in query:
            return None
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "mona_code": "ABC123",
            "assembly_number": 22,
            "name": "강테스트",
            "political_party": "테스트당",
            "election_district": "서울 테스트구",
            "election_type": "지역구",
            "reelection_count": 1,
            "profile_image_url": None,
        }

    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        fake_fetch_one,
    )
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_all",
        lambda query, params=(): [],
    )

    detail = MemberService.get_member_detail("abc123-22")

    assert detail["contradictory_speeches"] == [
        {
            "label": "과거 발언",
            "speech_text": "아직 비교 가능한 발언 후보가 준비되지 않았습니다.",
            "source": "자동 분석 준비 중",
            "tone": "past",
        },
        {
            "label": "최근 발언",
            "speech_text": "원문 발언 분석이 완료되면 이 영역에 표시됩니다.",
            "source": "자동 분석 준비 중",
            "tone": "recent",
        },
    ]
    assert detail["contradiction_summary"] is None


def test_member_service_uses_contradiction_candidate_when_available(monkeypatch):
    candidate = {
        "topic_label": "경제 정책",
        "summary": "과거에는 감세를 주장했으나 최근에는 증세를 주장함.",
        "matched_cues": ["감세", "증세"],
        "past_spoken_date": "2020-03-10",
        "past_speech_text": "세금을 낮춰야 경제가 살아납니다.",
        "past_original_url": "https://record.assembly.go.kr/past/1",
        "recent_spoken_date": "2025-11-05",
        "recent_speech_text": "지금은 복지 재원 마련을 위해 증세가 필요합니다.",
        "recent_original_url": "https://record.assembly.go.kr/recent/2",
    }

    def fake_fetch_one(query, params=()):
        if "COUNT(*)" in query:
            return {
                "total_speeches": 10,
                "total_meetings": 3,
                "latest_speech_date": "2025-11-05",
            }
        if "contradiction_candidates" in query:
            return candidate
        return {
            "id": "11111111-1111-1111-1111-111111111111",
            "mona_code": "ABC123",
            "assembly_number": 22,
            "name": "강테스트",
            "political_party": "테스트당",
            "election_district": "서울 테스트구",
            "election_type": "지역구",
            "reelection_count": 1,
            "profile_image_url": None,
        }

    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_one",
        fake_fetch_one,
    )
    monkeypatch.setattr(
        "backend.api.services.member_service.Database.fetch_all",
        lambda query, params=(): [],
    )

    detail = MemberService.get_member_detail("abc123-22")

    assert len(detail["contradictory_speeches"]) == 2
    assert detail["contradictory_speeches"][0]["tone"] == "past"
    assert detail["contradictory_speeches"][0]["speech_text"] == "세금을 낮춰야 경제가 살아납니다."
    assert detail["contradictory_speeches"][0]["source"] == "2020-03-10"
    assert detail["contradictory_speeches"][0]["original_url"] == "https://record.assembly.go.kr/past/1"
    assert detail["contradictory_speeches"][1]["tone"] == "recent"
    assert detail["contradictory_speeches"][1]["speech_text"] == "지금은 복지 재원 마련을 위해 증세가 필요합니다."
    assert detail["contradictory_speeches"][1]["source"] == "2025-11-05"
    assert detail["contradictory_speeches"][1]["original_url"] == "https://record.assembly.go.kr/recent/2"
    assert detail["contradiction_summary"] == "과거에는 감세를 주장했으나 최근에는 증세를 주장함."
