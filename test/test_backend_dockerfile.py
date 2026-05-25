from pathlib import Path


def test_backend_image_includes_pipeline_modules():
    """백엔드 이미지가 런타임 import에 필요한 pipelines 패키지를 포함한다."""
    dockerfile = Path("docker/backend.Dockerfile").read_text()

    assert "COPY backend/ backend/" in dockerfile
    assert "COPY pipelines/ pipelines/" in dockerfile
