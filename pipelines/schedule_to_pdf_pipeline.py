from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from loguru import logger

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.config import OPEN_GOVERMENT_API_KEY
from pipelines.utils.db_connections import get_postgres_connection
from pipelines.utils.incremental_helpers import (
    filter_new_dates,
    get_date_range_filter,
    get_existing_pdf_dates,
)
from pipelines.utils.request_utils import request_paginated_data
from pipelines.utils.url_constants import (
    MAIN_CONGRESS_SCHEDULE_URL,
    MAIN_CONGRESS_SPEECH_PDF_URL,
)


class CongressScheduleExtractor(BaseExtractor):
    """국회 일정 API에서 전체 일정 데이터를 수집합니다.

    Args:
        url: 일정 API URL입니다.
        unit_cd: 국회 대수 코드입니다. 기본값은 "100022"입니다.
        page_size: 페이지당 데이터 개수입니다.
        max_pages: 최대 요청 페이지 수입니다.
    """

    def __init__(self, url, unit_cd="100022", page_size=100, max_pages=100):
        self.url = url
        self.unit_cd = unit_cd
        self.page_size = page_size
        self.max_pages = max_pages

    def extract(self):
        """일정 API 데이터를 페이지 단위로 수집합니다.

        Returns:
            일정 API에서 받은 원본 row 목록입니다.
        """
        self.log_info(f"📢 CongressScheduleExtractor: Extracting from {self.url}")
        key_name = self.url[43:]
        base_params = {
            "KEY": OPEN_GOVERMENT_API_KEY,
            "Type": "json",
            "UNIT_CD": self.unit_cd,
        }
        all_data = request_paginated_data(
            self.url,
            base_params,
            key_name,
            page_size=self.page_size,
            max_pages=self.max_pages,
        )
        self.log_info(f"📌 전체 일정 데이터 로드 완료! 총 {len(all_data)}개 수집")
        return all_data


class PDFUrlExtractor(BaseExtractor):
    """회의 날짜별 국회 회의록 PDF URL 데이터를 수집합니다.

    Args:
        url: PDF URL API URL입니다.
        meeting_dates: PDF URL을 조회할 회의 날짜 목록입니다.
        unit_cd: 국회 대수 코드입니다.
        page_size: 페이지당 데이터 개수입니다.
        max_pages: 날짜별 최대 요청 페이지 수입니다.
    """

    def __init__(self, url, meeting_dates, unit_cd="22", page_size=100, max_pages=10):
        self.url = url
        self.meeting_dates = meeting_dates
        self.unit_cd = unit_cd
        self.page_size = page_size
        self.max_pages = max_pages

    def extract(self):
        """회의 날짜별 PDF URL 데이터를 병렬로 수집합니다.

        Returns:
            PDF URL 원본 row 목록과 실제로 응답이 있었던 날짜 목록 튜플입니다.
        """
        self.log_info("PDF URL 데이터를 가져옵니다.")
        key_name = self.url[43:]
        base_params = {
            "KEY": OPEN_GOVERMENT_API_KEY,
            "Type": "json",
            "DAE_NUM": self.unit_cd,
        }
        all_data, fetched_dates = [], set()

        def fetch_by_date(date):
            return date, request_paginated_data(
                self.url,
                base_params,
                key_name,
                date_key="CONF_DATE",
                date_value=date,
                page_size=self.page_size,
                max_pages=self.max_pages,
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_by_date, date) for date in self.meeting_dates
            ]
            for future in as_completed(futures):
                date, page_data = future.result()
                if page_data:
                    fetched_dates.add(date)
                    all_data.extend(page_data)

        self.log_info(f"📌 전체 PDF URL 데이터 로드 완료! 총 {len(all_data)}개 수집")
        return all_data, sorted(fetched_dates)


class CongressScheduleTransformer(BaseTransformer):
    """국회 일정 데이터에서 회의 날짜 목록을 추출합니다."""

    def transform(self, schedule_data: List[Dict]):
        """일정 원본 row에서 중복 없는 날짜 목록을 생성합니다.

        Args:
            schedule_data: 국회 일정 API 원본 row 목록입니다.

        Returns:
            정렬된 회의 날짜 목록입니다.
        """
        meeting_dates = sorted(set(item["MEETTING_DATE"] for item in schedule_data))
        return meeting_dates


class PDFUrlTransformer(BaseTransformer):
    """PDF URL 원본 row를 저장 가능한 형태로 병합합니다."""

    def transform(self, pdf_data_list: List[Dict]):
        """같은 회의의 PDF URL row를 하나의 데이터로 병합합니다.

        Args:
            pdf_data_list: PDF URL API 원본 row 목록입니다.

        Returns:
            PostgreSQL 저장용 PDF URL 데이터 목록입니다.
        """
        grouped = defaultdict(list)

        for item in pdf_data_list:
            key = (item.get("CONF_DATE"), item.get("TITLE"), item.get("CONFER_NUM"))
            grouped[key].append(item)

        transformed_data = []
        for (date, title, confer_num), group_items in grouped.items():
            merged = group_items[0].copy()
            merged["SUB_NAME"] = "\n".join(
                item.get("SUB_NAME", "") for item in group_items
            )
            transformed_data.append(
                {
                    "CONFER_NUM": merged.get("CONFER_NUM"),
                    "DAE_NUM": merged.get("DAE_NUM"),
                    "CONF_DATE": merged.get("CONF_DATE"),
                    "TITLE": merged.get("TITLE"),
                    "CLASS_NAME": merged.get("CLASS_NAME"),
                    "SUB_NAME": merged.get("SUB_NAME"),
                    "VOD_LINK_URL": merged.get("VOD_LINK_URL"),
                    "CONF_LINK_URL": merged.get("CONF_LINK_URL"),
                    "PDF_LINK_URL": merged.get("PDF_LINK_URL"),
                    "get_pdf": False,
                }
            )

        return transformed_data


class PDFUrlLoader(BaseLoader):
    """PDF URL 데이터를 PostgreSQL에 저장합니다."""

    def __init__(self, connection):
        super().__init__(connection)

    def create_table(self):
        """PDF URL 저장 테이블을 생성합니다."""
        query = """
            CREATE TABLE IF NOT EXISTS pdf_url (
                pdf_url_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                confer_number INT,
                dae_number INT,
                date DATE NOT NULL,
                title TEXT NOT NULL,
                class_name TEXT,
                sub_name TEXT,
                vod_link TEXT,
                conf_link TEXT,
                pdf_url TEXT,
                get_pdf BOOLEAN DEFAULT FALSE,
                CONSTRAINT unique_pdf UNIQUE (date, title, pdf_url)
            );
        """
        self._execute_query(query)
        logger.info("✅ pdf_url 테이블 생성 완료 (또는 이미 존재함)")

    def load(self, pdf_url_data):
        """PDF URL 데이터 한 건을 저장합니다.

        Args:
            pdf_url_data: PDF URL transformer가 반환한 데이터입니다.
        """
        try:
            logger.info(
                f"➕ PDF URL 삽입 시도: {pdf_url_data.get('date')} - {pdf_url_data.get('sub_name')}"
            )
            query = """
                INSERT INTO pdf_url (
                    confer_number, dae_number, date, title, class_name,
                    sub_name, vod_link, conf_link, pdf_url, get_pdf
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (date, title, pdf_url) DO NOTHING;
            """
            params = (
                pdf_url_data.get("CONFER_NUM"),
                pdf_url_data.get("DAE_NUM"),
                pdf_url_data.get("CONF_DATE"),
                pdf_url_data.get("TITLE"),
                pdf_url_data.get("CLASS_NAME"),
                pdf_url_data.get("SUB_NAME"),
                pdf_url_data.get("VOD_LINK_URL"),
                pdf_url_data.get("CONF_LINK_URL"),
                pdf_url_data.get("PDF_LINK_URL"),
                pdf_url_data.get("get_pdf", False),
            )
            result = self._execute_query(query, params)
            if result is not None:
                logger.debug(f"Query result: {result}")
            logger.success(
                f"✅ PDF URL 저장 성공: {pdf_url_data.get('date')} - {pdf_url_data.get('sub_name')}"
            )
        except Exception as e:
            logger.error(f"❌ PDF URL 저장 중 오류 발생: {str(e)}")
            raise


class ScheduleToPDFPipeline(BasePipeline):
    """국회 일정에서 회의록 PDF URL까지 수집하는 파이프라인입니다."""

    def __init__(
        self,
        unit_cd: str = "22",
        incremental: bool = True,
        days_back: Optional[int] = None,
    ):
        """파이프라인 구성요소를 초기화합니다.

        Args:
            unit_cd: 국회 대수 코드입니다. 예를 들어 "22"는 22대 국회입니다.
            incremental: True면 기존 날짜를 스킵하고, False면 전체 수집합니다.
            days_back: 최근 N일만 처리합니다. None이면 전체를 처리합니다.
        """
        self.incremental = incremental
        self.days_back = days_back
        self.connection = get_postgres_connection()

        self.schedule_extractor = CongressScheduleExtractor(
            url=MAIN_CONGRESS_SCHEDULE_URL
        )
        self.schedule_transformer = CongressScheduleTransformer()
        self.pdf_extractor = PDFUrlExtractor(
            url=MAIN_CONGRESS_SPEECH_PDF_URL,
            meeting_dates=[],
            unit_cd=unit_cd,
        )
        self.pdf_transformer = PDFUrlTransformer()
        self.loader = PDFUrlLoader(self.connection)

    def run(self):
        """일정 수집부터 PDF URL 저장까지 실행합니다.

        Returns:
            저장을 시도한 PDF URL 데이터 개수입니다.
        """
        # Step 1: 일정 추출
        logger.info("✅ 일정 extractor 시작")
        schedule_data = self.schedule_extractor.extract()
        logger.info("✅ 일정 데이터 추출 완료")

        # Step 2: 날짜 리스트 생성
        all_meeting_dates = self.schedule_transformer.transform(schedule_data)
        logger.info(f"✅ 전체 날짜 리스트: {len(all_meeting_dates)}건")

        # Step 2.5: 증분 필터링
        if self.incremental:
            existing_dates = get_existing_pdf_dates(self.connection)
            meeting_dates = filter_new_dates(all_meeting_dates, existing_dates)

            if not meeting_dates:
                logger.info("✅ 신규 날짜가 없습니다. 건너뜁니다.")
                return 0
        else:
            meeting_dates = all_meeting_dates

        # Step 2.6: 최근 N일 필터 적용
        if self.days_back:
            cutoff = get_date_range_filter(self.days_back)
            meeting_dates = [d for d in meeting_dates if d >= cutoff]
            logger.info(f"✅ 최근 {self.days_back}일 필터 적용: {len(meeting_dates)}건")

            if not meeting_dates:
                logger.info("✅ 필터 후 처리할 날짜가 없습니다.")
                return 0

        # Step 3: PDF URL 추출
        self.pdf_extractor.meeting_dates = meeting_dates
        logger.info("✅ PDF extractor 시작")
        pdf_data, fetched_dates = self.pdf_extractor.extract()
        logger.info(f"✅ PDF 데이터 추출 완료 ({len(pdf_data)}건)")

        # Step 4: 변환
        transformed_pdf_data = self.pdf_transformer.transform(pdf_data)
        logger.info(f"✅ PDF 데이터 변환 완료 ({len(transformed_pdf_data)}건)")

        # Step 5: DB 저장
        self.loader.create_table()
        for item in transformed_pdf_data:
            self.loader.load(item)

        logger.info("✅ PostgreSQL 저장 완료")
        return len(transformed_pdf_data)
