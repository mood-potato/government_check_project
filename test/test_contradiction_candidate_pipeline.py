"""Tests for the ContradictionCandidatePipeline."""

import json

import numpy as np
import pytest

from pipelines.contradiction_candidate_pipeline import (
    ContradictionCandidateExtractor,
    ContradictionCandidateLoader,
    ContradictionCandidateTransformer,
)


# ---------------------------------------------------------------------------
# Fake DB helpers
# ---------------------------------------------------------------------------
class FakeCursor:
    def __init__(self, fetchall_result=None, fetchone_result=None):
        self.executed = []
        self.fetchall_result = fetchall_result or []
        self.fetchone_result = fetchone_result

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.fetchall_result

    def fetchone(self):
        return self.fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, fetchall_result=None, fetchone_result=None):
        self.cursor_instance = FakeCursor(
            fetchall_result=fetchall_result,
            fetchone_result=fetchone_result,
        )
        self.commits = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1


# ---------------------------------------------------------------------------
# Fake embedding model
# ---------------------------------------------------------------------------
class FakeEmbeddingModel:
    """All pairs get a fixed similarity value by construction."""

    def __init__(self, fixed_similarity: float = 0.9):
        self._similarity = fixed_similarity

    def encode(self, texts, normalize_embeddings=True):
        result = []
        for i, _text in enumerate(texts):
            if i == 0:
                result.append(np.array([1.0, 0.0]))
            else:
                s = self._similarity
                result.append(np.array([s, (1 - s**2) ** 0.5]))
        return result


# ---------------------------------------------------------------------------
# Helper: build a minimal pair dict
# ---------------------------------------------------------------------------
def _make_pair(
    past_text: str,
    recent_text: str,
    past_date: str = "2024-01-01",
    recent_date: str = "2026-01-01",
    speaker_id: str = "aaaa-0000",
    past_id: str = "past-uuid-0001",
    recent_id: str = "recent-uuid-0001",
    recent_class_name: str = "환경노동위원회",
) -> dict:
    return {
        "speaker_id": speaker_id,
        "member_name": "홍길동",
        "mona_code": "MONO001",
        "assembly_number": 22,
        "political_party": "테스트당",
        "election_district": "서울 강남구",
        "profile_image_url": "https://example.com/profile.jpg",
        "recent_id": recent_id,
        "recent_date": recent_date,
        "recent_class_name": recent_class_name,
        "recent_speech_text": recent_text,
        "recent_original_url": "https://example.com/recent",
        "past_id": past_id,
        "past_date": past_date,
        "past_class_name": "환경노동위원회",
        "past_speech_text": past_text,
        "past_original_url": "https://example.com/past",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_only_past_before_recent_is_candidate():
    """과거 발언 날짜가 최근 발언보다 이전이고 단서가 있으면 후보로 선정됩니다."""
    model = FakeEmbeddingModel(fixed_similarity=0.9)
    transformer = ContradictionCandidateTransformer(model=model, similarity_threshold=0.6)

    # Pair A: valid — past < recent, has 강화/완화 cue
    pair_a = _make_pair(
        past_text="이 정책을 강화해야 합니다.",
        recent_text="이 정책을 완화해야 합니다.",
        past_date="2024-01-01",
        recent_date="2026-01-01",
        past_id="past-0001",
        recent_id="recent-0001",
    )

    # Pair B: same date — extractor would filter, but transformer ignores dates.
    # Supply it anyway to confirm transformer doesn't add extra date filtering.
    pair_b = _make_pair(
        past_text="찬성 의견을 표명합니다.",
        recent_text="반대 의견을 표명합니다.",
        past_date="2026-01-01",
        recent_date="2026-01-01",
        past_id="past-0002",
        recent_id="recent-0002",
    )

    results = transformer.transform([pair_a, pair_b])

    # Both pairs have valid cues and similarity above threshold.
    # Transformer does NOT filter by date — that's the extractor's job.
    result_ids = {c["past_speech_id"] for c in results}
    assert "past-0001" in result_ids
    assert "past-0002" in result_ids


def test_transformer_filters_by_similarity_threshold():
    """유사도가 임계값 미만이면 단서가 있어도 후보로 선정되지 않습니다."""
    # low similarity model: dot product ≈ 0.3 * 0.9 ≈ 0.27 (below threshold)
    # Actually with FakeEmbeddingModel(0.3): vec0=[1,0], vec1=[0.3, ~0.95]
    # dot product = 0.3 < 0.6 threshold
    low_model = FakeEmbeddingModel(fixed_similarity=0.3)
    transformer_low = ContradictionCandidateTransformer(
        model=low_model, similarity_threshold=0.6
    )

    high_model = FakeEmbeddingModel(fixed_similarity=0.9)
    transformer_high = ContradictionCandidateTransformer(
        model=high_model, similarity_threshold=0.6
    )

    pair = _make_pair(
        past_text="이 법안에 찬성합니다.",
        recent_text="이 법안에 반대합니다.",
        past_id="past-sim-001",
        recent_id="recent-sim-001",
    )

    # Low similarity → not a candidate
    low_results = transformer_low.transform([pair])
    assert low_results == []

    # High similarity → IS a candidate
    high_results = transformer_high.transform([pair])
    assert len(high_results) == 1
    assert high_results[0]["past_speech_id"] == "past-sim-001"


def test_transformer_detects_all_cue_pairs():
    """모든 CUE_PAIRS 키워드를 올바르게 감지합니다."""
    model = FakeEmbeddingModel(fixed_similarity=0.9)
    transformer = ContradictionCandidateTransformer(model=model, similarity_threshold=0.6)

    cue_test_cases = [
        ("찬성", "반대"),
        ("강화", "완화"),
        ("확대", "축소"),
        ("유지", "폐지"),
        ("필요", "불필요"),
    ]

    for i, (past_cue, recent_cue) in enumerate(cue_test_cases):
        pair = _make_pair(
            past_text=f"이 정책을 {past_cue}하는 것이 좋습니다.",
            recent_text=f"이 정책을 {recent_cue}하는 것이 필요합니다.",
            past_id=f"past-cue-{i:03d}",
            recent_id=f"recent-cue-{i:03d}",
        )
        results = transformer.transform([pair])
        assert len(results) == 1, f"cue pair ({past_cue}, {recent_cue}) not detected"
        assert past_cue in results[0]["matched_cues"], f"{past_cue} missing from matched_cues"
        assert recent_cue in results[0]["matched_cues"], f"{recent_cue} missing from matched_cues"


def test_transformer_rejects_pair_with_no_cues():
    """과거와 최근 발언에 동일한 방향의 단어만 있으면 후보로 선정되지 않습니다."""
    model = FakeEmbeddingModel(fixed_similarity=0.9)
    transformer = ContradictionCandidateTransformer(model=model, similarity_threshold=0.6)

    # Both have "강화" — no contradictory direction
    pair = _make_pair(
        past_text="이 정책을 강화해야 합니다.",
        recent_text="이 정책을 강화하는 방향이 바람직합니다.",
        past_id="past-nocue-001",
        recent_id="recent-nocue-001",
    )

    results = transformer.transform([pair])
    assert results == []


def test_loader_upserts_candidates_and_hero_snapshot():
    """후보를 upsert하고 마지막으로 home_section_snapshot을 업서트합니다."""
    connection = FakeConnection()
    loader = ContradictionCandidateLoader(connection)

    candidates = [
        {
            "speaker_id": "speaker-uuid-001",
            "past_speech_id": "past-uuid-001",
            "recent_speech_id": "recent-uuid-001",
            "topic_label": "환경노동위원회",
            "summary": "같은 쟁점에서 과거에는 '강화' 표현이, 최근에는 '완화' 표현이 함께 포착되어 비교 후보로 분류했습니다.",
            "score": 0.9,
            "matched_cues": ["강화", "완화"],
            "member_name": "홍길동",
            "mona_code": "MONO001",
            "assembly_number": 22,
            "political_party": "테스트당",
            "election_district": "서울 강남구",
            "profile_image_url": "https://example.com/profile.jpg",
            "past_date": "2024-01-01",
            "past_class_name": "환경노동위원회",
            "past_speech_text": "이 정책을 강화해야 합니다.",
            "past_original_url": "https://example.com/past",
            "recent_date": "2026-01-01",
            "recent_class_name": "환경노동위원회",
            "recent_speech_text": "이 정책을 완화해야 합니다.",
            "recent_original_url": "https://example.com/recent",
        },
        {
            "speaker_id": "speaker-uuid-002",
            "past_speech_id": "past-uuid-002",
            "recent_speech_id": "recent-uuid-002",
            "topic_label": "기획재정위원회",
            "summary": "같은 쟁점에서 과거에는 '확대' 표현이, 최근에는 '축소' 표현이 함께 포착되어 비교 후보로 분류했습니다.",
            "score": 0.7,
            "matched_cues": ["확대", "축소"],
            "member_name": "김철수",
            "mona_code": "MONO002",
            "assembly_number": 22,
            "political_party": "또다른당",
            "election_district": "부산 해운대구",
            "profile_image_url": "https://example.com/profile2.jpg",
            "past_date": "2023-06-01",
            "past_class_name": "기획재정위원회",
            "past_speech_text": "예산을 확대해야 합니다.",
            "past_original_url": "https://example.com/past2",
            "recent_date": "2026-02-01",
            "recent_class_name": "기획재정위원회",
            "recent_speech_text": "예산을 축소해야 합니다.",
            "recent_original_url": "https://example.com/recent2",
        },
    ]

    count = loader.load(candidates)

    executed = connection.cursor_instance.executed

    # Two contradiction_candidates upserts + one home_section_snapshot upsert
    assert len(executed) == 3

    # First two queries should be contradiction_candidates upserts
    assert "INSERT INTO contradiction_candidates" in executed[0][0]
    assert "INSERT INTO contradiction_candidates" in executed[1][0]

    # Last query should be home_section_snapshot upsert
    assert "INSERT INTO home_section_snapshot" in executed[2][0]

    # Verify hero payload corresponds to the best (first) candidate
    _, snapshot_params = executed[2]
    hero_payload = json.loads(snapshot_params[1])
    assert hero_payload["member"]["name"] == "홍길동"
    assert hero_payload["topic_label"] == "환경노동위원회"
    assert hero_payload["past_speech"]["spoken_date"] == "2024-01-01"
    assert hero_payload["recent_speech"]["spoken_date"] == "2026-01-01"

    # commits: 2 per candidate upsert + 1 for snapshot = 3
    assert connection.commits == 3
    assert count == 2


def test_loader_create_table():
    """create_table()은 contradiction_candidates 테이블 생성 쿼리를 실행합니다."""
    connection = FakeConnection()
    loader = ContradictionCandidateLoader(connection)

    loader.create_table()

    executed = connection.cursor_instance.executed
    assert len(executed) == 1
    query, params = executed[0]
    assert "CREATE TABLE IF NOT EXISTS contradiction_candidates" in query
    assert "uq_contradiction_pair" in query
    assert "idx_contradiction_speaker_created" in query
    assert connection.commits == 1


def test_extractor_returns_empty_when_no_connection():
    """connection이 None이면 빈 목록을 반환합니다."""
    extractor = ContradictionCandidateExtractor(connection=None)
    result = extractor.extract()
    assert result == []
