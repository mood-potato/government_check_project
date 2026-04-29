import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from loguru import logger
from tqdm import tqdm

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.common import OPEN_GOVERMENT_API_KEY
from pipelines.utils.db import get_postgres_connection
from pipelines.utils.openapi import (
    CONGRESS_BILL_CONF_LIST_URL,
    CONGRESS_BILL_LIST_URL,
    request_paginated_data,
)

ORDERED_BILL_NAME_PATTERN = re.compile(r"^\s*(\d+)\.\s*(.+)$")
NUMBER_PATTERN = re.compile(r"(\d+)")


def parse_korean_number(value: Optional[str]) -> Optional[int]:
    """한국어 라벨 문자열에서 첫 번째 숫자를 추출합니다.

    Args:
        value: "제22대", "제434회"처럼 숫자가 포함된 문자열입니다.

    Returns:
        추출한 정수입니다. 숫자가 없으면 None을 반환합니다.
    """
    if value is None:
        return None

    match = NUMBER_PATTERN.search(str(value))
    if not match:
        return None
    return int(match.group(1))


def split_bill_order(bill_name: Optional[str]) -> Tuple[Optional[int], str]:
    """안건명 앞의 순번을 분리합니다.

    Args:
        bill_name: "2. 방송법 일부개정법률안"처럼 순번이 포함된 안건명입니다.

    Returns:
        안건 순번과 순번을 제거한 안건명 튜플입니다.
    """
    if not bill_name:
        return None, ""

    match = ORDERED_BILL_NAME_PATTERN.match(bill_name)
    if not match:
        return None, bill_name.strip()

    return int(match.group(1)), match.group(2).strip()


def format_openapi_date(value: Optional[str]) -> Optional[str]:
    """국회 Open API 날짜 문자열을 ISO 날짜 문자열로 변환합니다.

    Args:
        value: YYYYMMDD 형식의 날짜 문자열입니다.

    Returns:
        YYYY-MM-DD 형식의 날짜 문자열입니다. 값이 없으면 None을 반환합니다.
    """
    if not value:
        return None

    return datetime.strptime(value, "%Y%m%d").date().isoformat()


# ======== BillInfoETL===========
# BillInfo는 BillUrl을 가져오기 위해 의안 번호를 가져오는 사이트임


class BillInfoExtractor(BaseExtractor):
    """국회 Open API에서 회의별 안건 목록을 수집합니다.

    Args:
        url: VCONFBILLLIST API 주소입니다.
        assembly_number: 수집할 국회 대수입니다.
        page_size: API 페이지당 요청할 row 수입니다.
        max_pages: 최대 요청 페이지 수입니다.
    """

    def __init__(
        self,
        url,
        assembly_number=22,
        page_size=1000,
        max_pages=300,
    ):
        self.url = url
        self.assembly_number = assembly_number
        self.page_size = page_size
        self.max_pages = max_pages

    # TODO: 날짜가 없어서 개수를 세서 증분 저장을 하도록 최신 몇개인지 가져오도록 수정해야함
    def extract(self):
        """안건 목록 원본 row를 수집합니다.

        Returns:
            VCONFBILLLIST API에서 받은 원본 row 딕셔너리 목록입니다.
        """
        self.log_info(f"회의별 의안 목록 데이터를 가져옵니다: {self.url}")
        key_name = self.url[43:]
        base_params = {
            "KEY": OPEN_GOVERMENT_API_KEY,
            "Type": "json",
        }
        if self.assembly_number:
            base_params["ERACO"] = f"제{self.assembly_number}대"

        # NOTE: 반복적으로 데이터를 가져오도록 설정함, 현재 최대 30만건까지 가져옴.
        rows = request_paginated_data(
            self.url,
            base_params,
            key_name,
            page_size=self.page_size,
            max_pages=self.max_pages,
        )
        self.log_info(f"회의별 의안 목록 데이터 로드 완료: 총 {len(rows)}개")
        return rows


class BillInfoTransformer(BaseTransformer):
    """안건 목록 API 응답을 bill_info 저장 형식으로 변환합니다."""

    def transform(self, data: List[Dict]) -> List[Dict]:
        """안건 목록 원본 row를 DB 저장용 row로 변환합니다.

        Args:
            data: VCONFBILLLIST API에서 받은 원본 row 목록입니다.

        Returns:
            bill_info 테이블 컬럼명에 맞춘 딕셔너리 목록입니다.
        """
        transformed = []
        self.log_info("회의별 의안 목록 데이터 전환 시작")

        for item in data:
            bill_order, bill_name = split_bill_order(item.get("BILL_NM"))
            transformed.append(
                {
                    "meeting_id": item.get("CONF_ID"),
                    "dae_number": parse_korean_number(item.get("ERACO")),
                    "session_number": parse_korean_number(item.get("SESS")),
                    "confer_number": parse_korean_number(item.get("DGR")),
                    "bill_id": item.get("BILL_ID"),
                    "bill_name": bill_name,
                    "bill_order": bill_order,
                    "detail_link": item.get("LINK_URL"),
                }
            )
        self.log_info(f"회의별 의안 목록 데이터 전환 완료: 총 {len(transformed)}개")

        return transformed


class BillInfoLoader(BaseLoader):
    """정규화된 안건 목록을 bill_info 테이블에 저장합니다.

    Args:
        connection: 쓰기에 사용할 PostgreSQL 연결 객체입니다.
    """

    def __init__(self, connection, run_id: Optional[str] = None):
        super().__init__(connection, run_id)

    def create_table(self):
        """bill_info 테이블과 인덱스를 생성합니다."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS bill_info (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                meeting_id TEXT NOT NULL,
                dae_number INT NOT NULL,
                session_number INT NOT NULL,
                confer_number INT NOT NULL,
                bill_id TEXT NOT NULL,
                bill_name TEXT NOT NULL,
                bill_order INT,
                detail_link TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bill_info_meeting_bill
            ON bill_info (meeting_id, bill_id);
            """,
            """CREATE INDEX IF NOT EXISTS idx_bill_info_bill_id ON bill_info (bill_id);""",
        ]
        for query in queries:
            self._execute_query(query)
        self.log_info("회의별 의안 목록 bill_info 테이블 준비 완료")

    def load(self, bill_info_data: Dict):
        """안건 목록 row 하나를 upsert합니다.

        Args:
            bill_info_data: bill_info 컬럼명에 맞춘 딕셔너리입니다.

        Returns:
            공통 쿼리 실행기가 반환한 결과입니다.
        """
        # TODO: Loader의 update로 인해 문제가 생기는 경우가 있는 지 확인해야 한다.
        query = """
            INSERT INTO bill_info (
                meeting_id,
                dae_number,
                session_number,
                confer_number,
                bill_id,
                bill_name,
                bill_order,
                detail_link
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (meeting_id, bill_id) DO UPDATE SET
                dae_number = EXCLUDED.dae_number,
                session_number = EXCLUDED.session_number,
                confer_number = EXCLUDED.confer_number,
                bill_name = EXCLUDED.bill_name,
                bill_order = EXCLUDED.bill_order,
                detail_link = EXCLUDED.detail_link
            RETURNING id, (xmax = 0) AS inserted;
        """
        params = (
            bill_info_data.get("meeting_id"),
            bill_info_data.get("dae_number"),
            bill_info_data.get("session_number"),
            bill_info_data.get("confer_number"),
            bill_info_data.get("bill_id"),
            bill_info_data.get("bill_name"),
            bill_info_data.get("bill_order"),
            bill_info_data.get("detail_link"),
        )
        result = self._execute_query(query, params)

        if self.run_id:
            if result and result[0].get("inserted"):
                action = "inserted"
            elif result:
                action = "updated"
            else:
                action = "skipped"

            self.log_load_row_event(
                target_table="bill_info",
                record_key=f"{bill_info_data.get('meeting_id')}:{bill_info_data.get('bill_id')}",
                action=action,
                meta={
                    "bill_name": bill_info_data.get("bill_name"),
                    "session_number": bill_info_data.get("session_number"),
                    "confer_number": bill_info_data.get("confer_number"),
                },
            )
        return result

    def load_many(self, bill_info_rows: Iterable[Dict]):
        """안건 목록 row 여러 개를 upsert합니다.

        Args:
            bill_info_rows: bill_info 컬럼명에 맞춘 딕셔너리 목록입니다.

        Returns:
            저장을 시도한 row 수입니다.
        """
        count = 0
        for row in bill_info_rows:
            self.load(row)
            count += 1
        return count


class BillInfoPipeline(BasePipeline):
    """회의별 의안목록을 수집해 옵니다.

    Args:
        assembly_number: 몇번 째, 국회의원인지 확인 함
        bill_info_page_size: 회의별 의안목록 API 페이지별 요청할 row 수입니다.
        bill_info_max_pages: 회의별 의안목록 API 최대 요청 페이지 수입니다.
    """

    def __init__(
        self,
        assembly_number: int = 22,
        bill_info_page_size=1000,
        bill_info_max_pages=300,
    ):

        self.connection = get_postgres_connection()
        self.run_id: Optional[str] = None
        self.now_time: datetime = datetime.now()

        self.extractor = BillInfoExtractor(
            url=CONGRESS_BILL_LIST_URL,
            assembly_number=assembly_number,
            page_size=bill_info_page_size,
            max_pages=bill_info_max_pages,
        )
        self.transformer = BillInfoTransformer()
        self.loader = BillInfoLoader(self.connection)

    def run(self):
        self.start_monitoring(
            pipeline_name="BillInfoPipeline",
            meta={
                "bill_info_page_size": self.extractor.page_size,
                "bill_info_max_pages": self.extractor.max_pages,
            },
        )
        self.loader.run_id = self.run_id

        try:
            self.log_info(
                f"회의별 의안목록에서 안건 목록 수집 시작 (run_id={self.run_id})"
            )
            raw_bill_info = self.extractor.extract()
            bill_info_rows = self.transformer.transform(raw_bill_info)
            self.log_info(
                f"{self.now_time}의 안건 목록 변환 완료: {len(bill_info_rows)}건"
            )

            self.loader.create_table()
            bill_info_count = self.loader.load_many(bill_info_rows)
            self.log_info(f"bill_info 저장 완료: {bill_info_count}건")

            self.finish_monitoring(status="success")
            return {
                "run_id": self.run_id,
                "bill_info": bill_info_count,
            }
        except Exception as exc:
            self.finish_monitoring(status="failed", error_message=str(exc))
            raise


# ======== BillUrlETL ===========
# BillUrl는 진짜 pdfurl을 보여주기 위해 만들어준 파일
class BillUrlExtractor(BaseExtractor):
    """안건 ID별 회의록 PDF 정보를 수집합니다.

    Args:
        url: VCONFBILLCONFLIST API 주소입니다.
        bill_ids: 회의록 PDF 정보를 조회할 안건 ID 목록입니다.
        page_size: API 페이지당 요청할 row 수입니다.
        max_pages: 안건별 최대 요청 페이지 수입니다.
        max_workers: 동시에 조회할 최대 안건 수입니다.
    """

    def __init__(
        self,
        url,
        bill_ids: Iterable[str],
        page_size=100,
        max_pages=10,
        max_workers=3,
    ):
        self.url = url
        self.bill_ids = list(bill_ids)
        self.page_size = page_size
        self.max_pages = max_pages
        self.max_workers = max_workers

    def extract(self) -> List[dict]:
        """안건 ID별 회의록 PDF 원본 row를 수집합니다.

        Returns:
            VCONFBILLCONFLIST API에서 받은 원본 row 딕셔너리 목록입니다.
        """
        self.log_info(f"안건 회의록 데이터를 가져옵니다: {len(self.bill_ids)}개 안건")
        key_name = self.url[43:]
        base_params = {
            "KEY": OPEN_GOVERMENT_API_KEY,
            "Type": "json",
        }

        def fetch_by_bill_id(bill_id):
            rows = request_paginated_data(
                self.url,
                base_params,
                key_name,
                date_key="BILL_ID",
                date_value=bill_id,
                page_size=self.page_size,
                max_pages=self.max_pages,
                show_progress=False,
            )
            return bill_id, rows

        all_rows = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(fetch_by_bill_id, bill_id)
                for bill_id in self.bill_ids
                if bill_id
            ]
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="안건별 회의록 URL 수집",
                unit="bill_url",
            ):
                bill_id, rows = future.result()
                logger.debug(f"{bill_id} 안건 회의록 {len(rows)}개 수집")
                all_rows.extend(rows)

        self.log_info(f"안건 회의록 데이터 로드 완료: 총 {len(all_rows)}개")
        return all_rows


class BillUrlTransformer(BaseTransformer):
    """안건 회의록 API 응답을 bill_url 저장 형식으로 변환합니다."""

    def transform(self, data: List[Dict]) -> List[Dict]:
        """안건 회의록 원본 row를 DB 저장용 row로 변환합니다.

        Args:
            data: VCONFBILLCONFLIST API에서 받은 원본 row 목록입니다.

        Returns:
            bill_url 테이블 컬럼명에 맞춘 딕셔너리 목록입니다.
        """
        transformed = []

        for item in data:
            _, agenda_name = split_bill_order(item.get("BILL_NM"))
            transformed.append(
                {
                    "agenda_id": item.get("BILL_ID"),
                    "agenda_name": agenda_name,
                    "meeting_type": item.get("CONF_KND"),
                    "meeting_id": item.get("CONF_ID"),
                    "dae_number": parse_korean_number(item.get("ERACO")),
                    "meeting_date": format_openapi_date(item.get("CONF_DT")),
                    "download_url": item.get("DOWN_URL"),
                    "get_pdf": False,
                }
            )

        self.log_info(f"안건 회의록 전환 완료: {len(transformed)}건")

        return transformed


class BillUrlLoader(BaseLoader):
    """정규화된 안건 회의록 PDF 정보를 bill_url 테이블에 저장합니다.

    Args:
        connection: 쓰기에 사용할 PostgreSQL 연결 객체입니다.
    """

    def __init__(self, connection, run_id: Optional[str] = None):
        super().__init__(connection, run_id)

    def create_table(self):
        """bill_url 테이블과 인덱스를 생성합니다."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS bill_url (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agenda_id TEXT NOT NULL,
                agenda_name TEXT NOT NULL,
                meeting_type TEXT NOT NULL,
                meeting_id TEXT NOT NULL,
                dae_number INT NOT NULL,
                meeting_date DATE NOT NULL,
                download_url TEXT NOT NULL,
                get_pdf BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_bill_url_agenda_meeting_download
            ON bill_url (agenda_id, meeting_id, download_url);
            """,
            """CREATE INDEX IF NOT EXISTS idx_bill_url_get_pdf ON bill_url (get_pdf);""",
            """CREATE INDEX IF NOT EXISTS idx_bill_url_agenda_id ON bill_url (agenda_id);""",
        ]
        for query in queries:
            self._execute_query(query)
        self.log_info("bill_url 테이블 준비 완료")

    def load(self, bill_url_data: Dict):
        """안건 회의록 PDF row 하나를 upsert합니다.

        Args:
            bill_url_data: bill_url 컬럼명에 맞춘 딕셔너리입니다.

        Returns:
            공통 쿼리 실행기가 반환한 결과입니다.
        """
        query = """
            INSERT INTO bill_url (
                agenda_id,
                agenda_name,
                meeting_type,
                meeting_id,
                dae_number,
                meeting_date,
                download_url,
                get_pdf
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (agenda_id, meeting_id, download_url) DO UPDATE SET
                agenda_name = EXCLUDED.agenda_name,
                meeting_type = EXCLUDED.meeting_type,
                dae_number = EXCLUDED.dae_number,
                meeting_date = EXCLUDED.meeting_date,
                get_pdf = bill_url.get_pdf
            RETURNING id, (xmax = 0) AS inserted;
        """
        params = (
            bill_url_data.get("agenda_id"),
            bill_url_data.get("agenda_name"),
            bill_url_data.get("meeting_type"),
            bill_url_data.get("meeting_id"),
            bill_url_data.get("dae_number"),
            bill_url_data.get("meeting_date"),
            bill_url_data.get("download_url"),
            bill_url_data.get("get_pdf", False),
        )
        result = self._execute_query(query, params)

        if self.run_id:
            if result and result[0].get("inserted"):
                action = "inserted"
            elif result:
                action = "updated"
            else:
                action = "skipped"

            self.log_load_row_event(
                target_table="bill_url",
                record_key=(
                    f"{bill_url_data.get('agenda_id')}:"
                    f"{bill_url_data.get('meeting_id')}:"
                    f"{bill_url_data.get('download_url')}"
                ),
                action=action,
                source_date=bill_url_data.get("meeting_date"),
                meta={
                    "agenda_name": bill_url_data.get("agenda_name"),
                    "meeting_type": bill_url_data.get("meeting_type"),
                },
            )
        return result

    def load_many(self, bill_url_rows: Iterable[Dict]):
        """안건 회의록 PDF row 여러 개를 upsert합니다.

        Args:
            bill_url_rows: bill_url 컬럼명에 맞춘 딕셔너리 목록입니다.

        Returns:
            저장을 시도한 row 수입니다.
        """
        count = 0
        for row in bill_url_rows:
            self.load(row)
            count += 1
        return count

    def fetch_pending_bill_ids(self) -> List[str]:
        """bill_info에는 있지만 bill_url에 아직 없는 안건 ID를 조회합니다."""
        query = """
            SELECT DISTINCT bi.bill_id
            FROM bill_info bi
            WHERE bi.bill_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM bill_url bu
                  WHERE bu.agenda_id = bi.bill_id
              )
            ORDER BY bi.bill_id;
        """
        rows = self._execute_query(query)
        return [row["bill_id"] for row in rows]


class BillUrlPipeline(BasePipeline):
    """의안별 회의록 목록을 바탕으로 PDF URL을 수집해 DB에 저장합니다.

    Args:
    """

    def __init__(
        self,
        bill_url_page_size=100,
        bill_url_max_pages=10,
        bill_url_max_workers=5,
    ):
        self.connection = get_postgres_connection()
        self.bill_url_page_size = bill_url_page_size
        self.bill_url_max_pages = bill_url_max_pages
        self.bill_url_max_workers = bill_url_max_workers

        self.transformer = BillUrlTransformer()
        self.loader = BillUrlLoader(self.connection)
        self.run_id: Optional[str] = None

    def run(self):
        self.start_monitoring(
            pipeline_name="BillUrlPipeline",
            meta={
                "bill_url_page_size": self.bill_url_page_size,
                "bill_url_max_pages": self.bill_url_max_pages,
                "bill_url_max_workers": self.bill_url_max_workers,
            },
        )
        self.loader.run_id = self.run_id

        try:
            self.log_info("수집해야할 안건 회의록 개수 확인")
            bill_ids_list = self.loader.fetch_pending_bill_ids()

            self.log_info(f"안건 회의록 수집 시작: {len(bill_ids_list)}개 안건")
            self.extractor = BillUrlExtractor(
                url=CONGRESS_BILL_CONF_LIST_URL,
                bill_ids=bill_ids_list,
                page_size=self.bill_url_page_size,
                max_pages=self.bill_url_max_pages,
                max_workers=self.bill_url_max_workers,
            )
            raw_bill_urls = self.extractor.extract()

            self.log_info(f"안건 회의록 전환 시작: {len(raw_bill_urls)}건")
            bill_url_rows = self.transformer.transform(raw_bill_urls)

            self.loader.create_table()
            bill_url_count = self.loader.load_many(bill_url_rows)
            self.log_info(f"bill_url 저장 완료: {bill_url_count}건")

            self.finish_monitoring(status="success")
            return {
                "run_id": self.run_id,
                "bill_url": bill_url_count,
            }
        except Exception as exc:
            self.finish_monitoring(status="failed", error_message=str(exc))
            raise


if __name__ == "__main__":
    bill_url_pipeline = BillUrlPipeline()
    bill_url_pipeline.run()
