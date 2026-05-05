from typing import Any

from backend.api.services.database import Database


DISCLAIMER = "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."


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

        return _member_detail(row)


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


def _member_detail(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "member": {
            **_member_ref(row),
            "generation_label": f"제{row['assembly_number']}대 국회의원",
            "committee_name": None,
            "status_label": row["election_type"] or "국회의원",
            "fact_summary": _speaker_fact_summary(row),
        },
        "metrics": [
            {"label": "대수", "value": f"{row['assembly_number']}대", "tone": "primary"},
            {"label": "정당", "value": row["political_party"]},
            {"label": "선거구", "value": row["election_district"] or "비례대표"},
        ],
        "conflicts": [],
        "contradictory_speeches": [
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
        ],
        "agendas": [],
        "similar_members": [],
        "opposing_members": [],
        "disclaimer": DISCLAIMER,
    }


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
