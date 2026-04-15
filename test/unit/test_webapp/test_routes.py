import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client with mocked database"""
    with patch("webapp.services.database.get_postgres_connection") as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.description = [("count",)]
        mock_cursor.fetchone.return_value = (0,)
        mock_cursor.fetchall.return_value = []

        conn = MagicMock()
        conn.closed = False
        conn.cursor.return_value = mock_cursor
        mock_conn.return_value = conn

        from api.main import app

        yield TestClient(app)


class TestHomeRoute:
    @patch("webapp.routes.home.MeetingService")
    def test_home_returns_200(self, mock_service, client):
        mock_service.get_stats.return_value = {
            "total_meetings": 100,
            "total_speeches": 5000,
            "total_speakers": 50,
            "latest_meeting": "2024-01-15",
        }
        mock_service.get_all.return_value = []
        mock_service.get_filter_options.return_value = {
            "class_names": [],
            "dae_numbers": [],
        }

        response = client.get("/")

        assert response.status_code == 200
        assert "국회 회의록 분석" in response.text


class TestMeetingsRoute:
    @patch("webapp.routes.meetings.MeetingService")
    def test_meetings_list_returns_200(self, mock_service, client):
        mock_service.get_all.return_value = []
        mock_service.get_filter_options.return_value = {
            "class_names": [],
            "dae_numbers": [],
        }

        response = client.get("/meetings")

        assert response.status_code == 200

    @patch("webapp.routes.meetings.MeetingService")
    def test_meetings_detail_404_for_invalid_id(self, mock_service, client):
        mock_service.get_by_id.return_value = None

        response = client.get("/meetings/invalid-id")

        assert response.status_code == 404


class TestSpeakersRoute:
    @patch("webapp.routes.speakers.SpeakerService")
    def test_speakers_list_returns_200(self, mock_service, client):
        mock_service.get_all.return_value = []
        mock_service.get_top_speakers.return_value = []

        response = client.get("/speakers")

        assert response.status_code == 200

    @patch("webapp.routes.speakers.SpeakerService")
    def test_speakers_detail_404_for_invalid_id(self, mock_service, client):
        mock_service.get_by_id.return_value = None

        response = client.get("/speakers/invalid-id")

        assert response.status_code == 404


class TestSearchRoute:
    @patch("webapp.routes.search.get_search_service")
    def test_search_page_returns_200(self, mock_get_service, client):
        mock_get_service.return_value = None

        response = client.get("/search")

        assert response.status_code == 200


class TestAPIRoutes:
    @patch("webapp.routes.api.MeetingService")
    def test_api_stats_returns_json(self, mock_service, client):
        mock_service.get_stats.return_value = {
            "total_meetings": 100,
            "total_speeches": 5000,
            "total_speakers": 50,
            "latest_meeting": "2024-01-15",
        }

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_meetings" in data

    @patch("webapp.routes.api.MeetingService")
    def test_api_meetings_returns_list(self, mock_service, client):
        mock_service.get_all.return_value = [
            {"pdf_url_id": "1", "title": "Test"}
        ]

        response = client.get("/api/meetings")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
