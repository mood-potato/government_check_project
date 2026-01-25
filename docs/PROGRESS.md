# Project Progress

## 2026-01-26: FastAPI Webapp Migration

### Summary
Streamlit 대시보드를 FastAPI + Jinja2 웹앱으로 마이그레이션 완료.

### Changes

#### Added
- `webapp/` - FastAPI 웹앱 전체 구조
  - `main.py` - FastAPI entry point
  - `config.py` - pydantic-settings 설정
  - `dependencies.py` - DI (templates, search service)
  - `routes/` - 5개 route handlers (home, meetings, speakers, search, api)
  - `services/` - 3개 service classes (database, meeting, speaker)
  - `templates/` - Jinja2 templates (Tailwind CSS)
  - `static/` - CSS, JS (Plotly.js charts)
- `test/unit/test_webapp/` - 15개 unit tests

#### Modified
- `pyproject.toml` - FastAPI dependencies 추가
  - fastapi>=0.115.0
  - uvicorn[standard]>=0.34.0
  - jinja2>=3.1.4
  - python-multipart>=0.0.20
  - pydantic-settings>=2.0.0

#### Removed
- `app/main.py` - 기존 Streamlit entry point
- `app/pages/search.py` - 기존 Streamlit search page

### Test Results
```
49 passed (34 existing + 15 new webapp tests)
```

### Commits
```
9ca6962 🔥 Remove: 기존 Streamlit 앱 삭제
a498c5d ✨ Add: FastAPI + Jinja2 webapp replacing Streamlit
```

### How to Run
```bash
# Start infrastructure
make up

# Run FastAPI webapp
uv run uvicorn webapp.main:app --reload --port 8000

# Open http://localhost:8000
```

---

## Previous Work (Before Migration)

### 4afe11a: 4가지 주요 기능 추가
- 증분 업데이트 (incremental updates)
- 테스트 코드
- 발언 요약 (LLM summarization)
- RAG 검색 (vector search)

### 68b63c3: 벡터화 기능 추가
- VectorizePipeline
- Qdrant integration
- sentence-transformers embeddings

### Earlier commits
- ETL 파이프라인 (ScheduleToPDFPipeline, PDFToSpeechPipeline)
- PostgreSQL schema (pdf_url, speakers, speeches)
- Open Assembly API integration
