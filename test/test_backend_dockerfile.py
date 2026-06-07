from pathlib import Path


def test_backend_image_includes_pipeline_modules():
    """백엔드 이미지가 런타임 import에 필요한 pipelines 패키지를 포함한다."""
    dockerfile = Path("docker/backend.Dockerfile").read_text()

    assert "COPY backend/ backend/" in dockerfile
    assert "COPY pipelines/ pipelines/" in dockerfile


def test_backend_image_extends_uv_download_timeout():
    """큰 ML wheel 다운로드 중 timeout이 쉽게 나지 않도록 uv timeout을 늘린다."""
    dockerfile = Path("docker/backend.Dockerfile").read_text()

    assert "UV_HTTP_TIMEOUT=1800" in dockerfile
    assert "UV_HTTP_RETRIES=10" in dockerfile
