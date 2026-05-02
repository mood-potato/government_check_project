import argparse
from typing import Any

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.common import OPEN_GOVERMENT_API_KEY
from pipelines.utils.db import get_postgres_connection
from pipelines.utils.openapi import request_paginated_data

ALLNAMEMBER_URL = "https://open.assembly.go.kr/portal/openapi/ALLNAMEMBER"
ALLNAMEMBER_KEY = "ALLNAMEMBER"
PROFILE_IMAGE_SOURCE = "open.assembly.go.kr ALLNAMEMBER"
PROFILE_IMAGE_LICENSE = "공공데이터포털 이용허락범위 제한 없음"


def clean_text(value: Any) -> str | None:
    """문자열 값을 정리합니다.

    Args:
        value: 정리할 원본 값입니다.

    Returns:
        앞뒤 공백을 제거한 문자열입니다. 비어 있으면 None입니다.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


class MemberPhotoExtractor(BaseExtractor):
    """열린국회정보 국회의원 정보 통합 API에서 의원 사진 row를 수집합니다."""

    def __init__(
        self,
        api_key: str | None = OPEN_GOVERMENT_API_KEY,
        page_size: int = 100,
        max_pages: int = 10,
        max_workers: int = 1,
        request_timeout: tuple[float, float] = (15, 60),
    ) -> None:
        """수집 설정을 저장합니다.

        Args:
            api_key: 열린국회정보 API 키입니다.
            page_size: 페이지당 요청 row 수입니다.
            max_pages: 최대 요청 페이지 수입니다.
            max_workers: 동시에 요청할 최대 페이지 수입니다.
            request_timeout: requests 연결/읽기 timeout입니다.
        """
        self.api_key = api_key
        self.page_size = page_size
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.request_timeout = request_timeout

    def extract(self) -> list[dict[str, Any]]:
        """ALLNAMEMBER API row를 수집합니다.

        Returns:
            API에서 받은 원본 row 목록입니다.

        Raises:
            ValueError: API 키가 설정되지 않은 경우입니다.
        """
        if not self.api_key:
            raise ValueError("OPEN_GOVERMENT_API_KEY is required")

        base_params = {
            "KEY": self.api_key,
            "Type": "json",
        }
        rows = request_paginated_data(
            ALLNAMEMBER_URL,
            base_params,
            ALLNAMEMBER_KEY,
            page_size=self.page_size,
            max_pages=self.max_pages,
            max_workers=self.max_workers,
            request_timeout=self.request_timeout,
        )
        if not rows:
            raise RuntimeError(
                "ALLNAMEMBER API returned no member rows. "
                "If open.assembly.go.kr is reachable in a browser, retry with "
                "larger --connect-timeout and --max-workers 1."
            )
        return rows


class MemberPhotoTransformer(BaseTransformer):
    """ALLNAMEMBER row를 `speakers` 사진 업데이트 row로 변환합니다."""

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, str]]:
        """원본 row에서 의원 코드와 사진 URL을 추출합니다.

        Args:
            data: ALLNAMEMBER API 원본 row 목록입니다.

        Returns:
            사진 URL이 있는 의원 row 목록입니다.
        """
        photos = []
        for item in data:
            mona_code = clean_text(item.get("NAAS_CD"))
            profile_image_url = clean_text(item.get("NAAS_PIC"))
            if mona_code is None or profile_image_url is None:
                continue

            photos.append(
                {
                    "mona_code": mona_code,
                    "name": clean_text(item.get("NAAS_NM")) or "",
                    "profile_image_url": profile_image_url,
                    "profile_image_source": PROFILE_IMAGE_SOURCE,
                    "profile_image_license": PROFILE_IMAGE_LICENSE,
                }
            )
        return photos


class MemberPhotoLoader(BaseLoader):
    """의원 사진 URL을 `speakers` 테이블에 저장합니다."""

    def __init__(self, connection: Any, assembly_number: int = 22) -> None:
        """DB 연결과 대상 국회 대수를 저장합니다.

        Args:
            connection: psycopg2 호환 DB 연결 객체입니다.
            assembly_number: 사진을 업데이트할 국회 대수입니다.
        """
        super().__init__(connection)
        self.assembly_number = assembly_number

    def create_table(self) -> None:
        """`speakers` 테이블에 사진 메타 컬럼을 보장합니다."""
        queries = [
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_url TEXT;",
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_source TEXT;",
            "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS profile_image_license TEXT;",
            (
                "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS "
                "profile_image_updated_at TIMESTAMPTZ;"
            ),
        ]
        for query in queries:
            self._execute_query(query)

    def load(self, photos: list[dict[str, str]]) -> int:
        """사진 row 목록을 `speakers`에 업데이트합니다.

        Args:
            photos: 변환된 의원 사진 row 목록입니다.

        Returns:
            업데이트를 시도한 row 수입니다.
        """
        query = """
            UPDATE speakers
            SET
                profile_image_url = %s,
                profile_image_source = %s,
                profile_image_license = %s,
                profile_image_updated_at = now(),
                updated_at = now()
            WHERE mona_code = %s
              AND assembly_number = %s
        """
        try:
            with self.connection.cursor() as cursor:
                for photo in photos:
                    cursor.execute(
                        query,
                        (
                            photo["profile_image_url"],
                            photo["profile_image_source"],
                            photo["profile_image_license"],
                            photo["mona_code"],
                            self.assembly_number,
                        ),
                    )
            self.connection.commit()
            return len(photos)
        except Exception:
            self.connection.rollback()
            raise


class MemberPhotoPipeline(BasePipeline):
    """의원 얼굴 사진 URL을 수집해 `speakers`에 저장합니다."""

    def __init__(
        self,
        assembly_number: int = 22,
        page_size: int = 100,
        max_pages: int = 10,
        max_workers: int = 1,
        request_timeout: tuple[float, float] = (15, 60),
    ) -> None:
        """파이프라인 구성요소를 초기화합니다.

        Args:
            assembly_number: 사진을 업데이트할 국회 대수입니다.
            page_size: API 페이지당 요청 row 수입니다.
            max_pages: 최대 요청 페이지 수입니다.
            max_workers: 동시에 요청할 최대 페이지 수입니다.
            request_timeout: requests 연결/읽기 timeout입니다.
        """
        connection = get_postgres_connection()
        loader = MemberPhotoLoader(connection, assembly_number=assembly_number)
        super().__init__(
            extractor=MemberPhotoExtractor(
                page_size=page_size,
                max_pages=max_pages,
                max_workers=max_workers,
                request_timeout=request_timeout,
            ),
            transformer=MemberPhotoTransformer(),
            loader=loader,
        )
        self.connection = connection

    def run(self) -> int:
        """의원 사진 수집과 저장을 실행합니다.

        Returns:
            저장을 시도한 사진 row 수입니다.
        """
        try:
            self.loader.create_table()
            rows = self.extractor.extract()
            photos = self.transformer.transform(rows)
            return self.loader.load(photos)
        finally:
            self.connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load National Assembly member profile image URLs."
    )
    parser.add_argument("--assembly-number", type=int, default=22)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--connect-timeout", type=float, default=15)
    parser.add_argument("--read-timeout", type=float, default=60)
    args = parser.parse_args()

    count = MemberPhotoPipeline(
        assembly_number=args.assembly_number,
        page_size=args.page_size,
        max_pages=args.max_pages,
        max_workers=args.max_workers,
        request_timeout=(args.connect_timeout, args.read_timeout),
    ).run()
    print(f"Loaded {count} member profile image URLs")


if __name__ == "__main__":
    main()
