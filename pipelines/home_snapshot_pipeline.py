import argparse
import json
from typing import Any

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.db import get_postgres_connection
from pipelines.utils.schema import load_table_ddl

DEFAULT_TTL_MINUTES = 10
DEFAULT_ASSEMBLY_NUMBER = 22
SPEECH_EXCERPT_LENGTH = 160


class HomeHeroSnapshotExtractor(BaseExtractor):
    """홈 히어로 후보 원본 데이터를 수집합니다."""

    def __init__(
        self,
        connection: Any | None = None,
        assembly_number: int = DEFAULT_ASSEMBLY_NUMBER,
    ) -> None:
        """수집 설정을 저장합니다.

        Args:
            connection: psycopg2 호환 DB 연결 객체입니다.
            assembly_number: 히어로 후보를 고를 국회 대수입니다.
        """
        self.connection = connection
        self.assembly_number = assembly_number

    def extract(self) -> dict[str, Any] | None:
        """히어로 스냅샷 원본 데이터를 반환합니다.

        Returns:
            아직 자동 분석 후보가 없으면 None을 반환합니다.
        """
        if self.connection is None:
            return None

        query = """
        SELECT
            sp.id::text AS member_id,
            sp.mona_code,
            sp.assembly_number,
            sp.name,
            sp.political_party,
            sp.election_district,
            sp.profile_image_url,
            recent.class_name AS meeting_name,
            recent.date::text AS recent_spoken_date,
            LEFT(recent.speech, %s) AS recent_speech_text,
            recent_source.original_url AS recent_original_url,
            past.date::text AS past_spoken_date,
            LEFT(past.speech, %s) AS past_speech_text,
            past.original_url AS past_original_url
        FROM speeches recent
        JOIN speakers sp
            ON sp.id = recent.speaker_id
        JOIN LATERAL (
            SELECT
                older.date,
                older.speech,
                COALESCE(p.conf_link, p.pdf_url, bu.download_url) AS original_url
            FROM speeches older
            LEFT JOIN pdf_url p
                ON older.pdf_url_id IN (
                    p.pdf_url_id::text,
                    CONCAT('pdf_url:', p.pdf_url_id::text)
                )
            LEFT JOIN bill_url bu
                ON older.pdf_url_id IN (
                    bu.id::text,
                    CONCAT('bill_url:', bu.id::text)
                )
            WHERE older.speaker_id = recent.speaker_id
              AND older.date < recent.date
            ORDER BY older.date ASC, older.speech_number ASC
            LIMIT 1
        ) past ON true
        LEFT JOIN pdf_url recent_pdf
            ON recent.pdf_url_id IN (
                recent_pdf.pdf_url_id::text,
                CONCAT('pdf_url:', recent_pdf.pdf_url_id::text)
            )
        LEFT JOIN bill_url recent_bill
            ON recent.pdf_url_id IN (
                recent_bill.id::text,
                CONCAT('bill_url:', recent_bill.id::text)
            )
        CROSS JOIN LATERAL (
            SELECT COALESCE(
                recent_pdf.conf_link,
                recent_pdf.pdf_url,
                recent_bill.download_url
            ) AS original_url
        ) recent_source
        WHERE recent.speaker_id IS NOT NULL
          AND sp.assembly_number = %s
        ORDER BY recent.date DESC, recent.speech_number DESC
        LIMIT 1
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    SPEECH_EXCERPT_LENGTH,
                    SPEECH_EXCERPT_LENGTH,
                    self.assembly_number,
                ),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_home_hero(row)


class HomeHeroSnapshotTransformer(BaseTransformer):
    """홈 히어로 원본 데이터를 API DTO로 변환합니다."""

    def transform(self, data: dict[str, Any] | None) -> dict[str, Any] | None:
        """히어로 원본 데이터를 저장 가능한 payload로 변환합니다.

        Args:
            data: 수집된 히어로 원본 데이터입니다.

        Returns:
            `HomeHeroDto`와 같은 형태의 dict입니다. 데이터가 없으면 None입니다.
        """
        return data


class HomeSnapshotLoader(BaseLoader):
    """홈 섹션 스냅샷을 `home_section_snapshot` 테이블에 저장합니다."""

    def create_table(self) -> None:
        """홈 섹션 스냅샷 테이블을 보장합니다."""
        with self.connection.cursor() as cursor:
            cursor.execute(load_table_ddl("home_section_snapshot"))
        self.connection.commit()

    def load(
        self,
        section_key: str,
        payload: dict[str, Any],
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ) -> str:
        """홈 섹션 payload를 upsert합니다.

        Args:
            section_key: 저장할 홈 섹션 키입니다.
            payload: JSONB로 저장할 DTO payload입니다.
            ttl_minutes: 스냅샷 만료 시간입니다.

        Returns:
            저장한 섹션 키입니다.
        """
        query = """
        INSERT INTO home_section_snapshot (
            section_key,
            payload,
            calculated_at,
            expires_at
        )
        VALUES (
            %s,
            %s::jsonb,
            now(),
            now() + (%s * interval '1 minute')
        )
        ON CONFLICT (section_key)
        DO UPDATE SET
            payload = EXCLUDED.payload,
            calculated_at = now(),
            expires_at = EXCLUDED.expires_at,
            version = home_section_snapshot.version + 1;
        """
        params = (section_key, json.dumps(payload, ensure_ascii=False), ttl_minutes)
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
        self.connection.commit()
        return section_key


class HomeSnapshotPipeline(BasePipeline):
    """홈 화면 섹션 스냅샷을 계산해 저장합니다."""

    def run(self) -> str | None:
        """홈 히어로 스냅샷을 생성합니다.

        Returns:
            저장된 섹션 키입니다. 히어로 후보가 없으면 None입니다.
        """
        self.loader.create_table()
        data = self.extractor.extract()
        payload = self.transformer.transform(data) if self.transformer else data
        if payload is None:
            self.log_info("저장할 홈 히어로 후보가 없습니다.")
            return None
        return self.loader.load("hero", payload)


def build_pipeline() -> HomeSnapshotPipeline:
    """기본 홈 스냅샷 파이프라인을 생성합니다.

    Returns:
        실행 가능한 홈 스냅샷 파이프라인입니다.
    """
    connection = get_postgres_connection()
    loader = HomeSnapshotLoader(connection)
    pipeline = HomeSnapshotPipeline(
        extractor=HomeHeroSnapshotExtractor(connection=connection),
        transformer=HomeHeroSnapshotTransformer(),
        loader=loader,
    )
    pipeline.connection = connection
    return pipeline


def _row_to_home_hero(row: Any) -> dict[str, Any]:
    """최근 발언자 row를 홈 히어로 DTO로 변환합니다.

    Args:
        row: DB cursor에서 반환한 row입니다.

    Returns:
        `HomeHeroDto` 형태의 dict입니다.
    """
    (
        member_id,
        mona_code,
        assembly_number,
        name,
        political_party,
        election_district,
        profile_image_url,
        meeting_name,
        recent_spoken_date,
        recent_speech_text,
        recent_original_url,
        past_spoken_date,
        past_speech_text,
        past_original_url,
    ) = row
    slug = f"{mona_code}-{assembly_number}".lower()
    topic_label = meeting_name or "최근 발언"

    return {
        "member": {
            "id": member_id,
            "slug": slug,
            "name": name,
            "party_name": political_party,
            "district_name": election_district,
            "profile_image_url": profile_image_url,
        },
        "topic_label": topic_label,
        "topic_slug": None,
        "past_speech": {
            "spoken_date": str(past_spoken_date),
            "meeting_name": topic_label,
            "speech_text": past_speech_text,
            "original_url": past_original_url,
        },
        "recent_speech": {
            "spoken_date": str(recent_spoken_date),
            "meeting_name": topic_label,
            "speech_text": recent_speech_text,
            "original_url": recent_original_url,
        },
        "summary": (
            f"{name} 의원의 최근 발언과 과거 발언을 함께 확인할 수 있는 "
            "비교 후보입니다."
        ),
    }


def main() -> None:
    """CLI에서 홈 스냅샷 파이프라인을 실행합니다."""
    parser = argparse.ArgumentParser(description="Build home section snapshots.")
    parser.parse_args()
    build_pipeline().run()


if __name__ == "__main__":
    main()
