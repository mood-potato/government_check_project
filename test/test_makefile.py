from pathlib import Path


def test_makefile_has_local_backend_and_frontend_targets():
    """Docker 없이 백엔드와 프런트엔드를 실행하는 타깃을 제공한다."""
    makefile = Path("makefile").read_text()

    assert "backend-local:" in makefile
    assert "uv run uvicorn backend.api.main:app --host 127.0.0.1 --port $(BACKEND_PORT) --reload" in makefile
    assert "frontend-local:" in makefile
    assert "cd frontend && BACKEND_URL=http://localhost:$(BACKEND_PORT) PORT=$(FRONTEND_PORT) bun run dev" in makefile
    assert "dev-local:" in makefile
