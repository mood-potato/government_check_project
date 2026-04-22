import requests
from loguru import logger
import json
from concurrent.futures import ThreadPoolExecutor

def request_paginated_data(
    url, base_params, key_name, date_key=None, date_value=None, page_size=100, max_pages=100
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

    Returns:
        list: 수집된 전체 row 데이터 리스트
    """
    all_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = executor.map(
            lambda idx: _fetch_single_page(url, base_params, key_name, date_key, date_value, page_size, idx),
            range(1, max_pages + 1)
        )
        for rows in futures:
            if not rows:
                break
            all_data.extend(rows)
    return all_data

def _fetch_single_page(url, base_params, key_name, date_key, date_value, page_size, pIndex):
    params = base_params.copy()
    params["pIndex"] = str(pIndex)
    params["pSize"] = str(page_size)
    if date_key and date_value:
        params[date_key] = date_value

    logger.debug(f"➡️ 요청 파라미터: {params}")
    try:
        response = requests.get(url=url, params=params, timeout=10)
        logger.info(f"📡 요청 중... pIndex={pIndex}, 요청 URL: {response.request.url}")
        response.raise_for_status()
        data = response.json()

        if "RESULT" in data and data["RESULT"]["MESSAGE"] == "해당하는 데이터가 없습니다.":
            logger.warning(f"📢 데이터 없음, pIndex={pIndex}")
            return []

        if key_name not in data:
            logger.error(f"❌ 예상된 키({key_name})가 응답 데이터에 없습니다.")
            return []

        rows = data[key_name][1].get("row", [])
        if isinstance(rows, dict):
            rows = [rows]
        logger.info(f"✅ {pIndex} 페이지 데이터 추가 (총 {len(rows)}개)")
        return rows
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"❌ 페이지 {pIndex} 처리 실패: {e}")
        return []
