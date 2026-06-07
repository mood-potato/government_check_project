from pathlib import Path
import unicodedata

from pipelines.run_pipeline import DEFAULT_STAGES, _resolve_existing_path, _split_stages


def test_frontend_uses_backend_service_url_in_compose():
    """프런트 컨테이너는 localhost가 아니라 backend 서비스명으로 API를 호출한다."""
    compose = Path("docker-compose.yaml").read_text()

    assert "BACKEND_URL: http://backend:8000" in compose


def test_pipeline_container_uses_run_pipeline_entrypoint():
    """파이프라인 컨테이너는 유지보수 가능한 Python 모듈 엔트리포인트를 사용한다."""
    dockerfile = Path("docker/pipeline.Dockerfile").read_text()

    assert 'CMD ["uv", "run", "python", "-m", "pipelines.run_pipeline"]' in dockerfile


def test_make_pipeline_starts_storage_services_first():
    """make pipeline은 공용 실행 스크립트를 호출한다."""
    makefile = Path("Makefile").read_text()

    assert "pipeline:" in makefile
    assert "scripts/run_pipeline.sh" in makefile
    assert "pipeline-bootstrap:" in makefile
    assert "scripts/run_pipeline.sh --build" in makefile


def test_pipeline_script_starts_storage_services_before_pipeline():
    """파이프라인 실행 스크립트는 저장소 서비스를 먼저 올린다."""
    script = Path("scripts/run_pipeline.sh").read_text()

    assert "up -d" in script
    assert "postgres elasticsearch" in script
    assert "--profile pipeline run --rm" in script
    assert "--reset" in script
    assert "SUPABASE_DATABASE_URL=" in script
    assert "--use-supabase" in script


def test_run_pipeline_default_stages_use_local_workbook_source():
    """기본 Docker 파이프라인은 포함된 workbook 기반 bill_url 적재를 사용한다."""
    assert _split_stages(None) == list(DEFAULT_STAGES)
    assert "bill-url-workbook" in DEFAULT_STAGES
    assert "bill-speech" in DEFAULT_STAGES


def test_run_pipeline_resolves_unicode_normalized_data_paths(tmp_path):
    """Docker Linux 환경에서도 macOS 정규화 파일명을 찾을 수 있다."""
    decomposed_name = "국회.csv"
    composed_name = "국회.csv"
    actual_path = tmp_path / decomposed_name
    actual_path.write_text("id,name\n1,테스트\n", encoding="utf-8")

    resolved_path = _resolve_existing_path(tmp_path / composed_name)

    assert resolved_path.exists()
    assert unicodedata.normalize("NFC", resolved_path.name) == unicodedata.normalize(
        "NFC", actual_path.name
    )
