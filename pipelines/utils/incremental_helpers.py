from datetime import datetime, timedelta
from typing import List, Set

from loguru import logger


def get_existing_pdf_dates(connection) -> Set[str]:
    """DB에 이미 저장된 PDF URL의 날짜 목록 조회"""
    query = "SELECT DISTINCT date FROM pdf_url"
    with connection.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        return {row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0]) for row in rows}


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
