# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

국회의원 회의록 분석 프로젝트 - 국회 회의록 PDF를 수집하고, 발언을 추출하여 분석하는 시스템.

## Commands

### Development
```bash
# Install dependencies (using uv)
uv sync

# Run tests
pytest test/unit/ -v

# Run all tests
pytest

# Run a specific test file
pytest test/unit/test_transformers.py -v

# Run with coverage
pytest --cov=modules
```

### Docker (Infrastructure)
```bash
make up        # Start containers (PostgreSQL, Qdrant)
make down      # Stop containers
make restart   # Restart containers
make logs      # View container logs
make ps        # List running containers
```

### Running Pipelines
```python
from modules.pipeline.schedule_to_pdf_pipeline import ScheduleToPDFPipeline
from modules.pipeline.pdf_to_speech_pipeline import PDFToSpeechPipeline
from modules.pipeline.vectorize_pipeline import VectorizePipeline

# 1. Extract congress schedule and PDF URLs (incremental by default)
ScheduleToPDFPipeline(unit_cd="22").run()

# Full re-fetch (skip incremental)
ScheduleToPDFPipeline(unit_cd="22", incremental=False).run()

# 2. Extract speeches from PDFs
PDFToSpeechPipeline().run()

# With summarization enabled (requires OPENAI_API_KEY)
# Set enable_summary=True in PDFToSpeechTransformer

# 3. Vectorize speeches for semantic search
VectorizePipeline().run()
```

### Streamlit Dashboard
```bash
streamlit run app/streamlit_app.py
```

## Architecture

### ETL Pipeline Pattern
The codebase follows an ETL (Extract-Transform-Load) pattern with abstract base classes in `modules/base/`:

- **BaseExtractor**: Extracts raw data from APIs or files
- **BaseTransformer**: Transforms raw data into structured format
- **BaseLoader**: Loads data into PostgreSQL/Qdrant
- **BasePipeline**: Orchestrates extractor → transformer → loader flow

### Main Pipelines

1. **ScheduleToPDFPipeline** (`modules/pipeline/schedule_to_pdf_pipeline.py`)
   - Fetches congress meeting schedules from Open Assembly API
   - Extracts PDF URLs for meeting transcripts
   - Supports incremental updates (`incremental=True`) and date filtering (`days_back=N`)

2. **PDFToSpeechPipeline** (`modules/pipeline/pdf_to_speech_pipeline.py`)
   - Downloads PDFs from stored URLs
   - Extracts text using pdfplumber
   - Parses individual speeches (speaker + text)
   - Optional: LLM-based summarization (`enable_summary=True`)

3. **VectorizePipeline** (`modules/pipeline/vectorize_pipeline.py`)
   - Extracts unvectorized speeches from PostgreSQL
   - Generates embeddings using sentence-transformers
   - Stores vectors in Qdrant for semantic search

### RAG/Vector Search
- `modules/rag/search_service.py` - Semantic search with filters (speaker, date)
- `modules/rag/speech_vectorizer.py` - sentence-transformers embeddings
- `modules/rag/qdrant_loader.py` - Qdrant vector storage

### LLM Integration
- `modules/llm/summarizer.py` - OpenAI GPT-based speech summarization

## Database Schema

### PostgreSQL Tables
- `pdf_url`: PDF metadata (date, title, url, get_pdf status)
- `speakers`: Unique speaker names
- `speeches`: Individual speech records with vectorized status

### Qdrant Collection
- `speeches`: Vector embeddings with payload (text, speaker, date, title)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
# PostgreSQL
POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT

# APIs
OPEN_GOVERMENT_API_KEY  # National Assembly Open API
OPENAI_API_KEY          # For summarization feature

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

## Key Directories

- `modules/` - Core ETL pipeline code
  - `base/` - Abstract base classes
  - `extract/` - Data extractors
  - `transform/` - Data transformers
  - `load/` - Data loaders
  - `pipeline/` - Pipeline orchestration
  - `rag/` - Vector search components
  - `llm/` - LLM integration
  - `utils/` - Helpers (db_connections, incremental_helpers)
- `app/` - React dashboard
- `test/` - pytest tests (unit/, integration/)
- `archive/` - Legacy/experimental code


## 하네스: 개발 프로세스

**목표:** 서비스 기획 → 피쳐 기획 → 설계 → 개발 → 검증 5단계 프로세스를 일관된 방식으로 실행한다.

**트리거:** 개발 프로세스 단계 관련 작업 요청 시 `dev-process-orchestrator` 스킬을 사용하라. 특정 단계 작업은 해당 스킬을 직접 사용한다.

**단계별 스킬:**
- 플로우 검토, 실패 케이스 발굴 → `flow-review`
- 케이스 목록 검토, 요구사항 검토 → `feature-validation`
- DB 스키마, API 명세 설계 → `schema-design`
- 태스크 구현, 수직 슬라이싱 → `dev-guide`
- 코드 리뷰, 버그 분석 → `code-review-process`
- Notion/CLAUDE.md 저장 → `notion-save`

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-04-11 | 초기 구성 | 전체 | 개발 프로세스 5단계 하네스 구축 |
| 2026-04-11 | flow-creator 에이전트 + flow-create 스킬 추가 | agents/flow-creator.md, skills/flow-create | 플로우 초안 생성 역할 공백 해소 |
| 2026-04-11 | feature-planner 에이전트 + feature-planning 스킬 추가 | agents/feature-planner.md, skills/feature-planning | flow-review → feature-validation 사이 기획 생성 역할 공백 해소 |
| 2026-04-11 | 오케스트레이터 7단계로 확장 | skills/dev-process-orchestrator | 생성 단계(1,3) 추가로 5단계 → 7단계 |
