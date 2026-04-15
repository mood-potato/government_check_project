# modules/extract/pdf_url_extractor.py
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.utils.config import OPEN_GOVERMENT_API_KEY
from modules.base.base_extractor import BaseExtractor
from modules.utils.request_utils import request_paginated_data


class PDFUrlExtractor(BaseExtractor):
    """_summary_

    Args:
        url (_type_): _설정된 PDF URL API URL_
        meeting_date_list (_type_): 이거 때문에 fetch_schedule을 통해서 schedule을 가져와야 함
        unit_cd (str, optional): 국회의원 선거 번호 fetch_schedule이랑은 또 다름. Defaults to "22".
        page_size (int, optional): 페이지의 크기. Defaults to 100.
        max_pages (int, optional): 최대 페이지 수. Defaults to 10.

    Returns:
        _type_: _description_
    """

    def __init__(self, url, meeting_dates, unit_cd="22", page_size=100, max_pages=10):
        self.url = url
        self.meeting_dates = meeting_dates
        self.unit_cd = unit_cd
        self.page_size = page_size
        self.max_pages = max_pages

    def extract(self):
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
