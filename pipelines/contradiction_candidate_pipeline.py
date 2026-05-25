import argparse
import json
from typing import Any, Optional

from loguru import logger

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.db import get_postgres_connection

# ---------------------------------------------------------------------------
# Contradiction cue pairs (past_cue, recent_cue)
# ---------------------------------------------------------------------------
CUE_PAIRS = [
    ("찬성", "반대"),
    ("강화", "완화"),
    ("확대", "축소"),
    ("유지", "폐지"),
    ("필요", "불필요"),
]


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------
class ContradictionCandidateExtractor(BaseExtractor):
    """상반 발언 후보 추출기: 최근 발언 + 동일 화자의 과거 발언 쌍을 수집합니다."""

    def __init__(
        self,
        connection: Any | None = None,
        recent_limit: int = 20,
        past_limit_per_speaker: int = 10,
        min_speech_chars: int = 50,
        assembly_number: int = 22,
    ) -> None:
        self.connection = connection
        self.recent_limit = recent_limit
        self.past_limit_per_speaker = past_limit_per_speaker
        self.min_speech_chars = min_speech_chars
        self.assembly_number = assembly_number

    def extract(self) -> list[dict[str, Any]]:
        """최근 발언과 동일 화자의 과거 발언 쌍 목록을 반환합니다.

        Returns:
            (recent, past) 쌍 dict 목록입니다. connection이 None이면 [] 반환.
        """
        if self.connection is None:
            return []

        recent_query = """
        SELECT
            r.id::text AS recent_id,
            r.speaker_id::text AS speaker_id,
            r.date::text AS recent_date,
            r.speech_number AS recent_speech_number,
            r.class_name AS recent_class_name,
            LEFT(r.speech, 500) AS recent_speech_text,
            LENGTH(r.speech) AS recent_speech_len,
            sp.name AS member_name,
            sp.mona_code,
            sp.assembly_number,
            sp.political_party,
            sp.election_district,
            sp.profile_image_url,
            COALESCE(rp.conf_link, rp.pdf_url, rb.download_url) AS recent_original_url
        FROM speeches r
        JOIN speakers sp ON sp.id = r.speaker_id
        LEFT JOIN pdf_url rp
            ON r.pdf_url_id IN (rp.pdf_url_id::text, CONCAT('pdf_url:', rp.pdf_url_id::text))
        LEFT JOIN bill_url rb
            ON r.pdf_url_id IN (rb.id::text, CONCAT('bill_url:', rb.id::text))
        WHERE r.speaker_id IS NOT NULL
          AND sp.assembly_number = %s
          AND LENGTH(r.speech) >= %s
        ORDER BY r.date DESC, r.speech_number DESC
        LIMIT %s
        """

        past_query = """
        SELECT
            p.id::text AS past_id,
            p.date::text AS past_date,
            p.speech_number AS past_speech_number,
            p.class_name AS past_class_name,
            LEFT(p.speech, 500) AS past_speech_text,
            LENGTH(p.speech) AS past_speech_len,
            COALESCE(pp.conf_link, pp.pdf_url, pb.download_url) AS past_original_url
        FROM speeches p
        LEFT JOIN pdf_url pp
            ON p.pdf_url_id IN (pp.pdf_url_id::text, CONCAT('pdf_url:', pp.pdf_url_id::text))
        LEFT JOIN bill_url pb
            ON p.pdf_url_id IN (pb.id::text, CONCAT('bill_url:', pb.id::text))
        WHERE p.speaker_id = %s
          AND LENGTH(p.speech) >= %s
        ORDER BY p.date ASC, p.speech_number ASC
        LIMIT %s
        """

        with self.connection.cursor() as cursor:
            cursor.execute(
                recent_query,
                (self.assembly_number, self.min_speech_chars, self.recent_limit),
            )
            recent_rows = cursor.fetchall()

        # Collect unique speaker_ids and their recent speech info
        recent_by_speaker: dict[str, list[dict]] = {}
        for row in recent_rows:
            (
                recent_id,
                speaker_id,
                recent_date,
                recent_speech_number,
                recent_class_name,
                recent_speech_text,
                recent_speech_len,
                member_name,
                mona_code,
                assembly_number,
                political_party,
                election_district,
                profile_image_url,
                recent_original_url,
            ) = row
            if speaker_id not in recent_by_speaker:
                recent_by_speaker[speaker_id] = []
            recent_by_speaker[speaker_id].append(
                {
                    "speaker_id": speaker_id,
                    "member_name": member_name,
                    "mona_code": mona_code,
                    "assembly_number": assembly_number,
                    "political_party": political_party,
                    "election_district": election_district,
                    "profile_image_url": profile_image_url,
                    "recent_id": recent_id,
                    "recent_date": recent_date,
                    "recent_class_name": recent_class_name,
                    "recent_speech_text": recent_speech_text,
                    "recent_original_url": recent_original_url,
                }
            )

        pairs: list[dict[str, Any]] = []

        for speaker_id, recent_speeches in recent_by_speaker.items():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    past_query,
                    (speaker_id, self.min_speech_chars, self.past_limit_per_speaker),
                )
                past_rows = cursor.fetchall()

            for recent in recent_speeches:
                for past_row in past_rows:
                    (
                        past_id,
                        past_date,
                        past_speech_number,
                        past_class_name,
                        past_speech_text,
                        past_speech_len,
                        past_original_url,
                    ) = past_row

                    # Only include pairs where past is strictly before recent
                    if past_date >= recent["recent_date"]:
                        continue
                    if past_id == recent["recent_id"]:
                        continue

                    pairs.append(
                        {
                            "speaker_id": speaker_id,
                            "member_name": recent["member_name"],
                            "mona_code": recent["mona_code"],
                            "assembly_number": recent["assembly_number"],
                            "political_party": recent["political_party"],
                            "election_district": recent["election_district"],
                            "profile_image_url": recent["profile_image_url"],
                            "recent_id": recent["recent_id"],
                            "recent_date": recent["recent_date"],
                            "recent_class_name": recent["recent_class_name"],
                            "recent_speech_text": recent["recent_speech_text"],
                            "recent_original_url": recent["recent_original_url"],
                            "past_id": past_id,
                            "past_date": past_date,
                            "past_class_name": past_class_name,
                            "past_speech_text": past_speech_text,
                            "past_original_url": past_original_url,
                        }
                    )

        self.log_info(f"{len(pairs)}개의 (recent, past) 발언 쌍을 수집했습니다.")
        return pairs


# ---------------------------------------------------------------------------
# Transformer
# ---------------------------------------------------------------------------
class ContradictionCandidateTransformer(BaseTransformer):
    """발언 쌍에서 상반 발언 후보를 감지합니다."""

    def __init__(
        self,
        model: Any,
        similarity_threshold: float = 0.6,
    ) -> None:
        self.model = model
        self.similarity_threshold = similarity_threshold

    def transform(self, pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """발언 쌍 목록을 받아 상반 발언 후보 목록을 반환합니다.

        Args:
            pairs: ContradictionCandidateExtractor.extract()가 반환한 쌍 목록입니다.

        Returns:
            상반 발언 후보 dict 목록 (score 내림차순 정렬).
        """
        if not pairs:
            return []

        # Step 1: Collect all unique speech texts and batch-encode
        unique_texts: list[str] = []
        seen: set[str] = set()
        for pair in pairs:
            for key in ("recent_speech_text", "past_speech_text"):
                text = pair.get(key) or ""
                if text and text not in seen:
                    unique_texts.append(text)
                    seen.add(text)

        embeddings_list = self.model.encode(unique_texts, normalize_embeddings=True)
        text_to_embedding: dict[str, Any] = {
            text: emb for text, emb in zip(unique_texts, embeddings_list)
        }

        candidates: list[dict[str, Any]] = []

        for pair in pairs:
            recent_text = pair.get("recent_speech_text") or ""
            past_text = pair.get("past_speech_text") or ""

            if not recent_text or not past_text:
                continue

            emb_recent = text_to_embedding.get(recent_text)
            emb_past = text_to_embedding.get(past_text)

            if emb_recent is None or emb_past is None:
                continue

            # Step 2: Cosine similarity (dot product of normalized vectors)
            similarity = float(emb_recent @ emb_past)

            if similarity < self.similarity_threshold:
                continue

            # Step 3: Detect contradiction cues
            matched_cues: list[str] = []
            matched_cue_pairs: list[tuple[str, str]] = []

            for cue_a, cue_b in CUE_PAIRS:
                if cue_a in past_text and cue_b in recent_text:
                    matched_cues.extend([cue_a, cue_b])
                    matched_cue_pairs.append((cue_a, cue_b))
                elif cue_b in past_text and cue_a in recent_text:
                    matched_cues.extend([cue_b, cue_a])
                    matched_cue_pairs.append((cue_b, cue_a))

            # Step 4: Only keep pairs with at least 1 matched cue pair
            if not matched_cue_pairs:
                continue

            # Step 5: Build candidate dict
            score = float(similarity * len(matched_cue_pairs))
            topic_label = pair.get("recent_class_name") or "발언 비교"

            candidates.append(
                {
                    "speaker_id": pair["speaker_id"],
                    "past_speech_id": pair["past_id"],
                    "recent_speech_id": pair["recent_id"],
                    "topic_label": topic_label,
                    "summary": _build_summary(matched_cues),
                    "score": score,
                    "matched_cues": matched_cues,
                    # hero DTO passthrough fields
                    "member_name": pair["member_name"],
                    "mona_code": pair["mona_code"],
                    "assembly_number": pair["assembly_number"],
                    "political_party": pair["political_party"],
                    "election_district": pair["election_district"],
                    "profile_image_url": pair["profile_image_url"],
                    "past_date": pair["past_date"],
                    "past_class_name": pair["past_class_name"],
                    "past_speech_text": pair["past_speech_text"],
                    "past_original_url": pair["past_original_url"],
                    "recent_date": pair["recent_date"],
                    "recent_class_name": pair["recent_class_name"],
                    "recent_speech_text": pair["recent_speech_text"],
                    "recent_original_url": pair["recent_original_url"],
                }
            )

        candidates.sort(key=lambda c: c["score"], reverse=True)
        self.log_info(f"{len(candidates)}개의 상반 발언 후보를 감지했습니다.")
        return candidates


def _build_summary(matched_cues: list[str]) -> str:
    """매칭된 단서 목록으로 요약문을 생성합니다.

    Args:
        matched_cues: 감지된 단서 키워드 목록입니다.

    Returns:
        요약 문자열입니다.
    """
    if len(matched_cues) >= 2:
        return (
            f"같은 쟁점에서 과거에는 '{matched_cues[0]}' 표현이, "
            f"최근에는 '{matched_cues[1]}' 표현이 함께 포착되어 비교 후보로 분류했습니다."
        )
    return "발언 내용에서 상반되는 표현이 포착되어 비교 후보로 분류했습니다."


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
class ContradictionCandidateLoader(BaseLoader):
    """상반 발언 후보를 DB에 upsert합니다."""

    def create_table(self) -> None:
        """contradiction_candidates 테이블과 인덱스를 보장합니다."""
        query = """
        CREATE TABLE IF NOT EXISTS contradiction_candidates (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            speaker_id       UUID        NOT NULL REFERENCES speakers (id),
            past_speech_id   UUID        NOT NULL REFERENCES speeches (id),
            recent_speech_id UUID        NOT NULL REFERENCES speeches (id),
            topic_label      TEXT        NOT NULL,
            summary          TEXT        NOT NULL,
            score            FLOAT       NOT NULL DEFAULT 0.0,
            matched_cues     TEXT[]      NOT NULL DEFAULT '{}',
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_contradiction_pair UNIQUE (past_speech_id, recent_speech_id)
        );
        CREATE INDEX IF NOT EXISTS idx_contradiction_speaker_created
        ON contradiction_candidates (speaker_id, created_at DESC);
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query)
        self.connection.commit()

    def load(self, candidates: list[dict[str, Any]]) -> int:
        """상반 발언 후보를 upsert하고 최우수 후보를 홈 스냅샷에도 저장합니다.

        Args:
            candidates: ContradictionCandidateTransformer.transform() 결과 목록입니다.

        Returns:
            저장된 후보 수입니다.
        """
        if not candidates:
            return 0

        upsert_query = """
        INSERT INTO contradiction_candidates
            (speaker_id, past_speech_id, recent_speech_id, topic_label, summary, score, matched_cues)
        VALUES (%s, %s::uuid, %s::uuid, %s, %s, %s, %s)
        ON CONFLICT (past_speech_id, recent_speech_id)
        DO UPDATE SET
            topic_label = EXCLUDED.topic_label,
            summary = EXCLUDED.summary,
            score = EXCLUDED.score,
            matched_cues = EXCLUDED.matched_cues
        """

        saved = 0
        for candidate in candidates:
            params = (
                candidate["speaker_id"],
                candidate["past_speech_id"],
                candidate["recent_speech_id"],
                candidate["topic_label"],
                candidate["summary"],
                candidate["score"],
                candidate["matched_cues"],
            )
            with self.connection.cursor() as cursor:
                cursor.execute(upsert_query, params)
            self.connection.commit()
            saved += 1

        # Upsert the best candidate as the hero section snapshot
        best = candidates[0]
        slug = f"{best['mona_code']}-{best['assembly_number']}".lower()
        hero_payload = {
            "member": {
                "id": best["speaker_id"],
                "slug": slug,
                "name": best["member_name"],
                "party_name": best["political_party"],
                "district_name": best["election_district"],
                "profile_image_url": best["profile_image_url"],
            },
            "topic_label": best["topic_label"],
            "topic_slug": None,
            "past_speech": {
                "spoken_date": best["past_date"],
                "meeting_name": best["past_class_name"] or best["topic_label"],
                "speech_text": best["past_speech_text"],
                "original_url": best["past_original_url"],
            },
            "recent_speech": {
                "spoken_date": best["recent_date"],
                "meeting_name": best["recent_class_name"] or best["topic_label"],
                "speech_text": best["recent_speech_text"],
                "original_url": best["recent_original_url"],
            },
            "summary": best["summary"],
        }

        ttl_minutes = 10080  # 1 week
        snapshot_query = """
        INSERT INTO home_section_snapshot (section_key, payload, calculated_at, expires_at)
        VALUES (%s, %s::jsonb, now(), now() + (%s * interval '1 minute'))
        ON CONFLICT (section_key)
        DO UPDATE SET
            payload = EXCLUDED.payload,
            calculated_at = now(),
            expires_at = EXCLUDED.expires_at,
            version = home_section_snapshot.version + 1;
        """
        snapshot_params = (
            "hero",
            json.dumps(hero_payload, ensure_ascii=False),
            ttl_minutes,
        )
        with self.connection.cursor() as cursor:
            cursor.execute(snapshot_query, snapshot_params)
        self.connection.commit()

        self.log_info(f"{saved}개의 상반 발언 후보를 저장했습니다.")
        return saved


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class ContradictionCandidatePipeline(BasePipeline):
    """상반 발언 후보 파이프라인: 추출 → 변환 → 저장."""

    def __init__(
        self,
        extractor: ContradictionCandidateExtractor,
        transformer: ContradictionCandidateTransformer,
        loader: ContradictionCandidateLoader,
        connection: Any | None = None,
    ) -> None:
        super().__init__(extractor=extractor, loader=loader, transformer=transformer)
        self.connection = connection

    def run(self) -> int:
        """상반 발언 후보를 탐색하고 저장합니다.

        Returns:
            저장된 후보 수입니다.
        """
        self.loader.create_table()
        pairs = self.extractor.extract()
        candidates = self.transformer.transform(pairs)
        if not candidates:
            self.log_info("상반 발언 후보가 없습니다.")
            return 0
        count = self.loader.load(candidates)
        self.log_info(f"상반 발언 후보 {count}개를 저장했습니다.")
        return count


# ---------------------------------------------------------------------------
# Factory & entry point
# ---------------------------------------------------------------------------
def build_pipeline(
    recent_limit: int = 20,
    past_limit_per_speaker: int = 10,
    similarity_threshold: float = 0.6,
    min_speech_chars: int = 50,
    assembly_number: int = 22,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> ContradictionCandidatePipeline:
    """기본 상반 발언 후보 파이프라인을 생성합니다.

    Returns:
        실행 가능한 ContradictionCandidatePipeline입니다.
    """
    from sentence_transformers import SentenceTransformer

    connection = get_postgres_connection()
    model = SentenceTransformer(model_name)
    extractor = ContradictionCandidateExtractor(
        connection=connection,
        recent_limit=recent_limit,
        past_limit_per_speaker=past_limit_per_speaker,
        min_speech_chars=min_speech_chars,
        assembly_number=assembly_number,
    )
    transformer = ContradictionCandidateTransformer(
        model=model,
        similarity_threshold=similarity_threshold,
    )
    loader = ContradictionCandidateLoader(connection)
    pipeline = ContradictionCandidatePipeline(
        extractor=extractor,
        transformer=transformer,
        loader=loader,
        connection=connection,
    )
    return pipeline


def main() -> None:
    """CLI에서 상반 발언 후보 파이프라인을 실행합니다."""
    parser = argparse.ArgumentParser(
        description="Detect contradiction candidate speech pairs."
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=20,
        help="최근 발언 조회 개수 (기본값: 20)",
    )
    parser.add_argument(
        "--past-limit-per-speaker",
        type=int,
        default=10,
        help="화자별 과거 발언 조회 개수 (기본값: 10)",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.6,
        help="코사인 유사도 임계값 (기본값: 0.6)",
    )
    parser.add_argument(
        "--min-speech-chars",
        type=int,
        default=50,
        help="최소 발언 길이 (기본값: 50)",
    )
    args = parser.parse_args()
    build_pipeline(
        recent_limit=args.recent_limit,
        past_limit_per_speaker=args.past_limit_per_speaker,
        similarity_threshold=args.similarity_threshold,
        min_speech_chars=args.min_speech_chars,
    ).run()


if __name__ == "__main__":
    main()
