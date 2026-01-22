from typing import Optional

from loguru import logger

from modules.base.base_pipeline import BasePipeline
from modules.constants.url_constants import (
    MAIN_CONGRESS_SCHEDULE_URL,
    MAIN_CONGRESS_SPEECH_PDF_URL,
)
from modules.extract.congress_schedule_extractor import CongressScheduleExtractor
from modules.extract.pdf_url_extractor import PDFUrlExtractor
from modules.load.pdf_url_loader import PDFUrlLoader
from modules.transform.congress_schedule_transformer import CongressScheduleTransformer
from modules.transform.pdf_url_transformer import PDFUrlTransformer
from modules.utils.db_connections import get_postgres_connection
from modules.utils.incremental_helpers import (
    filter_new_dates,
    get_date_range_filter,
    get_existing_pdf_dates,
)


class ScheduleToPDFPipeline(BasePipeline):
    def __init__(self, unit_cd: str = "22", incremental: bool = True, days_back: Optional[int] = None):
        """
        Args:
            unit_cd: 국회 대수 코드 (예: "22" = 22대 국회)
            incremental: True면 기존 날짜 스킵, False면 전체 수집
            days_back: 최근 N일만 처리 (None이면 전체)
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
