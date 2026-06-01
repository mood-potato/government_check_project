from pathlib import Path


def test_frontend_uses_backend_service_url_in_compose():
    """프런트 컨테이너는 localhost가 아니라 backend 서비스명으로 API를 호출한다."""
    compose = Path("docker-compose.yaml").read_text()

    assert "BACKEND_URL: http://backend:8000" in compose
