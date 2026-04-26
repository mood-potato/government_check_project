import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List, Set

import requests
from loguru import logger
from tqdm import tqdm

MAIN_CONGRESS_SCHEDULE_URL = (
    "https://open.assembly.go.kr/portal/openapi/nekcaiymatialqlxr"
)
MAIN_CONGRESS_SPEECH_PDF_URL = (
    "https://open.assembly.go.kr/portal/openapi/nzbyfwhwaoanttzje"
)
CONGRESS_BILL_LIST_URL = "https://open.assembly.go.kr/portal/openapi/VCONFBILLLIST"
CONGRESS_BILL_CONF_LIST_URL = (
    "https://open.assembly.go.kr/portal/openapi/VCONFBILLCONFLIST"
)

# HACK: 코드가 하나 줄음 : 단점은 플레이라이트나 bs4 사용시 불안정, 장점은 명시적이고 확실함. 하지만, 데이터를 가져오는 방법은 안정적인 API로 진행하자.
# CONGRESS_BILL_CONF_PAGE_URL = "https://open.assembly.go.kr/portal/data/service/selectServicePage.do/OOWY4R001216HX11526"
# CONGRESS_BILL_CONF_DOWNLOAD_CSV_XPATH ="/html/body/div[3]/div[7]/div/div[2]/div/div/div/section[2]/ul/li/dl/dd/a[2]"

DEFAULT_MAX_WORKERS = 3
DEFAULT_REQUEST_TIMEOUT = (3.05, 30)


def request_paginated_data(
    url,
    base_params,
    key_name,
    date_key=None,
    date_value=None,
    page_size=100,
    max_pages=100,
    max_workers=DEFAULT_MAX_WORKERS,
    request_timeout=DEFAULT_REQUEST_TIMEOUT,
    show_progress=True,
):
    """
    페이징 처리된 데이터를 반복적으로 요청하여 모두 수집하는 함수입니다.

    Args:
        url (str): 요청할 API URL
        base_params (dict): 기본 요청 파라미터 (API 키 등)
        key_name (str): 응답 JSON에서 실제 데이터가 담긴 key 이름
        date_key (str, optional): 특정 날짜 필터를 위한 파라미터 이름 (예: "CONF_DATE")
        date_value (str, optional): 날짜 필터로 사용할 값
        page_size (int, optional): 페이지당 데이터 개수. 기본값은 100
        max_pages (int, optional): 최대 페이지 수. 기본값은 100
        max_workers (int, optional): 동시에 요청할 최대 페이지 수. 기본값은 3
        request_timeout (tuple, optional): requests connect/read timeout입니다.
        show_progress (bool, optional): tqdm 진행률 표시 여부입니다.

    Returns:
        list: 수집된 전체 row 데이터 리스트
    """
    all_data = []
    stop_requested = False
    description = f"{key_name} 페이지 수집"

    with tqdm(
        total=max_pages,
        desc=description,
        unit="page",
        leave=False,
        disable=not show_progress,
    ) as progress:
        for start_page in range(1, max_pages + 1, max_workers):
            end_page = min(start_page + max_workers, max_pages + 1)
            page_indexes = range(start_page, end_page)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = executor.map(
                    lambda idx: _fetch_single_page(
                        url,
                        base_params,
                        key_name,
                        date_key,
                        date_value,
                        page_size,
                        idx,
                        request_timeout,
                    ),
                    page_indexes,
                )

                for rows in futures:
                    progress.update(1)
                    if not rows:
                        stop_requested = True
                        break
                    all_data.extend(rows)

            if stop_requested:
                break
    return all_data


def _fetch_single_page(
    url, base_params, key_name, date_key, date_value, page_size, pIndex, request_timeout
):
    params = base_params.copy()
    params["pIndex"] = str(pIndex)
    params["pSize"] = str(page_size)
    if date_key and date_value:
        params[date_key] = date_value

    logger.debug(f"요청 파라미터: {params}")
    try:
        response = requests.get(url=url, params=params, timeout=request_timeout)
        logger.debug(f"요청 중... pIndex={pIndex}, 요청 URL: {response.request.url}")
        response.raise_for_status()
        data = response.json()

        if (
            "RESULT" in data
            and data["RESULT"]["MESSAGE"] == "해당하는 데이터가 없습니다."
        ):
            logger.debug(f"데이터 없음, pIndex={pIndex}")
            return []

        if key_name not in data:
            logger.error(f"❌ 예상된 키({key_name})가 응답 데이터에 없습니다.")
            return []

        rows = data[key_name][1].get("row", [])
        if isinstance(rows, dict):
            rows = [rows]
        logger.debug(f"{pIndex} 페이지 데이터 추가 (총 {len(rows)}개)")
        return rows
    except (
        requests.exceptions.RequestException,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ) as e:
        logger.error(f"❌ 페이지 {pIndex} 처리 실패: {e}")
        return []


def get_existing_pdf_dates(connection) -> Set[str]:
    """DB에 이미 저장된 PDF URL의 날짜 목록 조회"""
    query = "SELECT DISTINCT date FROM pdf_url"
    with connection.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        return {
            row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0])
            for row in rows
        }


def get_existing_pdf_urls(connection) -> Set[str]:
    """DB에 이미 저장된 PDF URL 목록 조회"""
    query = "SELECT pdf_url FROM pdf_url WHERE pdf_url IS NOT NULL"
    with connection.cursor() as cur:
        cur.execute(query)
        return {row[0] for row in cur.fetchall()}


def filter_new_dates(all_dates: List[str], existing_dates: Set[str]) -> List[str]:
    """새로운 날짜만 필터링"""
    new_dates = [d for d in all_dates if d not in existing_dates]
    logger.info(f"전체 {len(all_dates)}개 중 {len(new_dates)}개 신규 날짜 발견")
    return new_dates


def get_date_range_filter(days_back: int = 30) -> str:
    """최근 N일 이내 날짜 필터 반환"""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    return cutoff_date.strftime("%Y-%m-%d")
