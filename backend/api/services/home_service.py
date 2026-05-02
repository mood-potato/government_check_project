from typing import Any

from backend.api.services.database import Database


DISCLAIMER = "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."


class HomeService:
    @staticmethod
    def get_home(limit: int = 12) -> dict[str, Any]:
        """홈 화면에 표시할 실제 의원 데이터를 반환합니다."""
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
            WHERE assembly_number = (SELECT MAX(assembly_number) FROM speakers)
            ORDER BY name
            LIMIT %s
            """,
            (limit,),
        )

        return {
            "hero": None,
            "popular_keywords": [],
            "recent_cases": [],
            "featured_members": [
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
            ],
            "disclaimer": DISCLAIMER,
        }


def _speaker_summary(row: dict[str, Any]) -> str:
    parts = [
        f"{row['assembly_number']}대",
        row["political_party"],
        row["election_district"],
    ]
    return " ".join(part for part in parts if part)
