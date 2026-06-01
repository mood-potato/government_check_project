from typing import Any

from backend.api.services.database import Database


DISCLAIMER = "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
RECENT_SPEECH_LIMIT = 5


class MemberService:
    @staticmethod
    def get_members(limit: int = 200, offset: int = 0) -> dict[str, Any]:
        """전체 의원 프로필 목록 화면 DTO를 반환합니다.

        Args:
            limit: 반환할 의원 수입니다.
            offset: 건너뛸 의원 수입니다.

        Returns:
            React 목록 화면이 바로 렌더링할 수 있는 의원 프로필 목록 DTO입니다.
        """
        rows = Database.fetch_all(
            """
            SELECT
                id::text,
                mona_code,
                assembly_number,
                name,
                political_party,
                election_district,
                profile_image_url
            FROM speakers
            ORDER BY assembly_number DESC, name ASC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

        return {
            "items": [
                {
                    "member": _member_ref(row),
                    "summary": _speaker_summary(row),
                }
                for row in rows
            ],
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def get_member_detail(member_slug: str) -> dict[str, Any] | None:
        """slug로 의원 상세 화면 DTO를 반환합니다.

        Args:
            member_slug: `{mona_code}-{assembly_number}` 형식의 의원 slug입니다.

        Returns:
            의원 상세 화면 DTO입니다. 찾을 수 없으면 None을 반환합니다.
        """
        parsed_slug = _parse_member_slug(member_slug)
        if parsed_slug is None:
            return None

        mona_code, assembly_number = parsed_slug
        row = Database.fetch_one(
            """
            SELECT
                id::text,
                mona_code,
                assembly_number,
                name,
                political_party,
                election_district,
                election_type,
                reelection_count,
                profile_image_url
            FROM speakers
            WHERE UPPER(mona_code) = %s AND assembly_number = %s
            """,
            (mona_code, assembly_number),
        )

        if row is None:
            return None

        activity = Database.fetch_one(
            """
            SELECT
                COUNT(*) AS total_speeches,
                COUNT(DISTINCT pdf_url_id) AS total_meetings,
                MAX(date) AS latest_speech_date
            FROM speeches
            WHERE speaker_id = %s
            """,
            (row["id"],),
        )
        recent_speeches = Database.fetch_all(
            """
            SELECT
                s.id::text AS id,
                s.date AS spoken_date,
                COALESCE(p.title, bu.agenda_name, s.class_name) AS meeting_name,
                LEFT(s.speech, 300) AS speech_text,
                COALESCE(p.conf_link, p.pdf_url, bu.download_url) AS original_url
            FROM (
                SELECT
                    id,
                    pdf_url_id,
                    date,
                    class_name,
                    speech,
                    speech_number
                FROM speeches
                WHERE speaker_id = %s
                ORDER BY date DESC, speech_number DESC
                LIMIT %s
            ) s
            LEFT JOIN pdf_url p
                ON s.pdf_url_id IN (p.pdf_url_id::text, CONCAT('pdf_url:', p.pdf_url_id::text))
            LEFT JOIN bill_url bu
                ON s.pdf_url_id IN (bu.id::text, CONCAT('bill_url:', bu.id::text))
            ORDER BY s.date DESC, s.speech_number DESC
            """,
            (row["id"], RECENT_SPEECH_LIMIT),
        )

        contradictory_candidate = Database.fetch_one(
            """
            SELECT
                cc.topic_label,
                cc.summary,
                cc.matched_cues,
                past_s.date::text AS past_spoken_date,
                LEFT(past_s.speech, 300) AS past_speech_text,
                COALESCE(pp.conf_link, pp.pdf_url, pb.download_url) AS past_original_url,
                recent_s.date::text AS recent_spoken_date,
                LEFT(recent_s.speech, 300) AS recent_speech_text,
                COALESCE(rp.conf_link, rp.pdf_url, rb.download_url) AS recent_original_url
            FROM contradiction_candidates cc
            JOIN speeches past_s ON past_s.id = cc.past_speech_id
            JOIN speeches recent_s ON recent_s.id = cc.recent_speech_id
            LEFT JOIN pdf_url pp
                ON past_s.pdf_url_id IN (pp.pdf_url_id::text, CONCAT('pdf_url:', pp.pdf_url_id::text))
            LEFT JOIN bill_url pb
                ON past_s.pdf_url_id IN (pb.id::text, CONCAT('bill_url:', pb.id::text))
            LEFT JOIN pdf_url rp
                ON recent_s.pdf_url_id IN (rp.pdf_url_id::text, CONCAT('pdf_url:', rp.pdf_url_id::text))
            LEFT JOIN bill_url rb
                ON recent_s.pdf_url_id IN (rb.id::text, CONCAT('bill_url:', rb.id::text))
            WHERE cc.speaker_id = %s
            ORDER BY cc.created_at DESC
            LIMIT 1
            """,
            (row["id"],),
        )

        return _member_detail(row, activity or {}, _recent_speech_dtos(recent_speeches), contradictory_candidate)


def _parse_member_slug(member_slug: str) -> tuple[str, int] | None:
    slug_parts = member_slug.rsplit("-", 1)
    if len(slug_parts) != 2:
        return None

    mona_code, assembly_number_text = slug_parts
    if not mona_code or not assembly_number_text.isdigit():
        return None

    return mona_code.upper(), int(assembly_number_text)


def _member_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "slug": f"{row['mona_code']}-{row['assembly_number']}".lower(),
        "name": row["name"],
        "party_name": row["political_party"],
        "district_name": row["election_district"],
        "profile_image_url": row["profile_image_url"],
    }


def _member_detail(
    row: dict[str, Any],
    activity: dict[str, Any],
    recent_speeches: list[dict[str, Any]],
    contradictory_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if contradictory_candidate is not None:
        contradictory_speeches = [
            {
                "label": "과거 발언",
                "speech_text": contradictory_candidate["past_speech_text"],
                "source": contradictory_candidate["past_spoken_date"] or "날짜 미상",
                "tone": "past",
                "original_url": contradictory_candidate["past_original_url"],
            },
            {
                "label": "최근 발언",
                "speech_text": contradictory_candidate["recent_speech_text"],
                "source": contradictory_candidate["recent_spoken_date"] or "날짜 미상",
                "tone": "recent",
                "original_url": contradictory_candidate["recent_original_url"],
            },
        ]
        contradiction_summary = contradictory_candidate["summary"]
    else:
        contradictory_speeches = [
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
        contradiction_summary = None

    return {
        "member": {
            **_member_ref(row),
            "generation_label": f"제{row['assembly_number']}대 국회의원",
            "committee_name": None,
            "status_label": row["election_type"] or "국회의원",
            "fact_summary": _speaker_fact_summary(row),
        },
        "metrics": _activity_metrics(row, activity),
        "conflicts": [],
        "contradictory_speeches": contradictory_speeches,
        "contradiction_summary": contradiction_summary,
        "recent_speeches": recent_speeches,
        "agendas": [],
        "similar_members": [],
        "opposing_members": [],
        "disclaimer": DISCLAIMER,
    }


def _activity_metrics(
    row: dict[str, Any], activity: dict[str, Any]
) -> list[dict[str, str]]:
    latest_speech_date = activity.get("latest_speech_date")
    return [
        {
            "label": "총 발언 수",
            "value": str(activity.get("total_speeches") or 0),
            "supporting_text": "건",
            "tone": "primary",
        },
        {
            "label": "참여 회의 수",
            "value": str(activity.get("total_meetings") or 0),
            "supporting_text": "회",
        },
        {
            "label": "최근 발언일",
            "value": _format_date(latest_speech_date) if latest_speech_date else "기록 없음",
        },
        {"label": "대수", "value": f"{row['assembly_number']}대"},
    ]


def _recent_speech_dtos(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "spoken_date": _format_iso_date(row["spoken_date"]),
        }
        for row in rows
    ]


def _format_date(value: Any) -> str:
    return str(value).replace("-", ".")


def _format_iso_date(value: Any) -> str:
    return str(value)


def _speaker_summary(row: dict[str, Any]) -> str:
    parts = [
        f"{row['assembly_number']}대",
        row["political_party"],
        row["election_district"],
    ]
    return " ".join(part for part in parts if part)


def _speaker_fact_summary(row: dict[str, Any]) -> str:
    parts = [_speaker_summary(row)]
    reelection_count = row.get("reelection_count")
    if reelection_count:
        parts.append(_reelection_label(reelection_count))
    parts.append("의원")
    return " ".join(parts)


def _reelection_label(reelection_count: int) -> str:
    if reelection_count <= 1:
        return "초선"
    if reelection_count == 2:
        return "재선"
    return f"{reelection_count}선"
