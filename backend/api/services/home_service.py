from typing import Any

from backend.api.services.database import Database


DISCLAIMER = "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."


class HomeService:
    @staticmethod
    def get_home(limit: int = 12) -> dict[str, Any]:
        """홈 화면에 표시할 실제 의원 데이터를 반환합니다."""
        return {
            "hero": HomeService.get_home_hero(),
            "popular_keywords": [],
            "recent_cases": HomeService.get_recent_cases(),
            "featured_members": HomeService.get_featured_members(limit=limit),
            "disclaimer": DISCLAIMER,
        }

    @staticmethod
    def get_home_hero() -> dict[str, Any] | None:
        """미리 계산된 홈 히어로 스냅샷을 반환합니다."""
        row = Database.fetch_one(
            """
            SELECT
                payload,
                calculated_at,
                expires_at
            FROM home_section_snapshot
            WHERE section_key = %s
            """,
            ("hero",),
        )
        if row is None:
            return None
        return row["payload"]

    @staticmethod
    def get_recent_cases() -> list[dict[str, Any]]:
        """홈 화면 추가 분석 사례를 반환합니다."""
        return []

    @staticmethod
    def get_featured_members(limit: int = 12) -> list[dict[str, Any]]:
        """홈 화면 최근 발언 인물 목록을 반환합니다."""
        rows = Database.fetch_all(
            """
            SELECT
                sp.id::text,
                sp.mona_code,
                sp.assembly_number,
                sp.name,
                sp.political_party,
                sp.election_district,
                sp.profile_image_url
            FROM speakers sp
            WHERE sp.assembly_number = (SELECT MAX(assembly_number) FROM speakers)
            ORDER BY sp.name ASC
            LIMIT %s
            """,
            (limit,),
        )

        return [
            {
                "rank": index,
                "member": {
                    "id": row["id"],
                    "slug": f"{row['mona_code']}-{row['assembly_number']}".lower(),
                    "name": row["name"],
                    "party_name": row["political_party"],
                    "district_name": row["election_district"],
                    "profile_image_url": row["profile_image_url"],
                },
                "summary": _speaker_summary(row),
            }
            for index, row in enumerate(rows, start=1)
        ]


def _speaker_summary(row: dict[str, Any]) -> str:
    speech_count = row.get("speech_count") or 0
    latest_speech_date = row.get("latest_speech_date")
    if speech_count and latest_speech_date:
        return f"최근 발언 {_format_date(latest_speech_date)} · {speech_count}건"

    parts = [
        f"{row['assembly_number']}대",
        row["political_party"],
        row["election_district"],
    ]
    return " ".join(part for part in parts if part)


def _format_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y.%m.%d")
    return str(value).replace("-", ".")
