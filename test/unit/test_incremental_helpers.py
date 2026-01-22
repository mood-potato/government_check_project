import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from modules.utils.incremental_helpers import (
    get_existing_pdf_dates,
    get_existing_pdf_urls,
    filter_new_dates,
    get_date_range_filter,
)


class TestGetExistingPdfDates:
    def test_returns_set_of_dates(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # datetime 객체 반환하는 경우
        cursor.fetchall.return_value = [
            (datetime(2024, 1, 15),),
            (datetime(2024, 1, 16),),
        ]

        result = get_existing_pdf_dates(connection)

        assert isinstance(result, set)
        assert "2024-01-15" in result
        assert "2024-01-16" in result

    def test_handles_string_dates(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        # 문자열로 반환하는 경우
        cursor.fetchall.return_value = [("2024-01-15",), ("2024-01-16",)]

        result = get_existing_pdf_dates(connection)

        assert "2024-01-15" in result
        assert "2024-01-16" in result

    def test_returns_empty_set_when_no_data(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []

        result = get_existing_pdf_dates(connection)

        assert result == set()


class TestGetExistingPdfUrls:
    def test_returns_set_of_urls(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        connection.cursor.return_value.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = [
            ("http://example.com/pdf1",),
            ("http://example.com/pdf2",),
        ]

        result = get_existing_pdf_urls(connection)

        assert isinstance(result, set)
        assert "http://example.com/pdf1" in result
        assert "http://example.com/pdf2" in result


class TestFilterNewDates:
    def test_filters_out_existing_dates(self):
        all_dates = ["2024-01-15", "2024-01-16", "2024-01-17"]
        existing_dates = {"2024-01-15", "2024-01-16"}

        result = filter_new_dates(all_dates, existing_dates)

        assert result == ["2024-01-17"]

    def test_returns_all_when_none_exist(self):
        all_dates = ["2024-01-15", "2024-01-16"]
        existing_dates = set()

        result = filter_new_dates(all_dates, existing_dates)

        assert result == ["2024-01-15", "2024-01-16"]

    def test_returns_empty_when_all_exist(self):
        all_dates = ["2024-01-15", "2024-01-16"]
        existing_dates = {"2024-01-15", "2024-01-16"}

        result = filter_new_dates(all_dates, existing_dates)

        assert result == []

    def test_preserves_order(self):
        all_dates = ["2024-01-17", "2024-01-15", "2024-01-18"]
        existing_dates = {"2024-01-15"}

        result = filter_new_dates(all_dates, existing_dates)

        assert result == ["2024-01-17", "2024-01-18"]


class TestGetDateRangeFilter:
    def test_returns_cutoff_date(self):
        result = get_date_range_filter(days_back=30)

        expected = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert result == expected

    def test_returns_correct_format(self):
        result = get_date_range_filter(days_back=7)

        # YYYY-MM-DD 형식 검증
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # 년도
        assert len(parts[1]) == 2  # 월
        assert len(parts[2]) == 2  # 일

    def test_default_is_30_days(self):
        result = get_date_range_filter()

        expected = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        assert result == expected
