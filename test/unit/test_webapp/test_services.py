import pytest
from unittest.mock import patch, MagicMock
from datetime import date


class TestDatabase:
    @patch("webapp.services.database.get_postgres_connection")
    def test_get_connection_creates_new_connection(self, mock_get_conn):
        from webapp.services.database import Database

        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_get_conn.return_value = mock_conn

        Database._conn = None
        conn = Database.get_connection()

        assert conn == mock_conn
        mock_get_conn.assert_called_once()

    @patch("webapp.services.database.get_postgres_connection")
    def test_fetch_all_returns_list_of_dicts(self, mock_get_conn):
        from webapp.services.database import Database

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "test"), (2, "test2")]

        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        Database._conn = None
        result = Database.fetch_all("SELECT * FROM test")

        assert result == [{"id": 1, "name": "test"}, {"id": 2, "name": "test2"}]

    @patch("webapp.services.database.get_postgres_connection")
    def test_fetch_one_returns_dict_or_none(self, mock_get_conn):
        from webapp.services.database import Database

        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchone.return_value = (1, "test")

        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        Database._conn = None
        result = Database.fetch_one("SELECT * FROM test WHERE id = 1")

        assert result == {"id": 1, "name": "test"}


class TestMeetingService:
    @patch("webapp.services.meeting_service.Database")
    def test_get_stats_returns_four_metrics(self, mock_db):
        from webapp.services.meeting_service import MeetingService

        mock_date = MagicMock()
        mock_date.strftime.return_value = "2024-01-15"

        mock_db.fetch_one.side_effect = [
            {"count": 100},
            {"count": 5000},
            {"count": 50},
            {"latest": mock_date},
        ]

        stats = MeetingService.get_stats()

        assert "total_meetings" in stats
        assert "total_speeches" in stats
        assert "total_speakers" in stats
        assert "latest_meeting" in stats
        assert stats["total_meetings"] == 100
        assert stats["total_speeches"] == 5000

    @patch("webapp.services.meeting_service.Database")
    def test_get_all_with_filters(self, mock_db):
        from webapp.services.meeting_service import MeetingService

        mock_db.fetch_all.return_value = [
            {"pdf_url_id": "1", "title": "Test Meeting", "speaker_count": 5}
        ]

        result = MeetingService.get_all(class_name="법제사법위원회", limit=10)

        assert len(result) == 1
        mock_db.fetch_all.assert_called_once()


class TestSpeakerService:
    @patch("webapp.services.speaker_service.Database")
    def test_get_all_with_search(self, mock_db):
        from webapp.services.speaker_service import SpeakerService

        mock_db.fetch_all.return_value = [
            {"id": "1", "name": "홍길동", "speech_count": 100}
        ]

        result = SpeakerService.get_all(name_search="홍")

        assert len(result) == 1
        assert result[0]["name"] == "홍길동"

    @patch("webapp.services.speaker_service.Database")
    def test_get_stats_returns_aggregates(self, mock_db):
        from webapp.services.speaker_service import SpeakerService

        mock_db.fetch_one.return_value = {
            "total_speeches": 100,
            "total_meetings": 20,
            "total_committees": 5,
            "avg_speech_length": 500.5,
        }

        stats = SpeakerService.get_stats("speaker-id")

        assert stats["total_speeches"] == 100
        assert stats["avg_speech_length"] == 500
