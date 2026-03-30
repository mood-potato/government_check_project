# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

Available gstack skills: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`.

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
- `app/` - Streamlit dashboard
- `test/` - pytest tests (unit/, integration/)
- `archive/` - Legacy/experimental code

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
