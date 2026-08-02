# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

국회의원 회의록 분석 프로젝트 - 국회 회의록 PDF를 수집하고, 발언을 추출하여 분석하는 시스템. `AGENTS.md`에 제품 방향과 코드 스타일이, `CONTEXT.md`에 용어집이 정리되어 있다 — 작업 전에 먼저 읽는다.

## Commands

### Development
```bash
# Install dependencies (using uv)
uv sync

# Run tests (testpaths = ["test"], flat directory — test/unit/ 하위 폴더 없음)
pytest

# Run a specific test file
pytest test/test_contradiction_candidate_pipeline.py -v

# Run with coverage
pytest --cov=pipelines --cov=backend
```

### Docker (Infrastructure)
```bash
make up        # Start containers (postgres, elasticsearch, backend, frontend, pipeline, airflow, caddy)
make down      # Stop containers
make restart   # Restart containers
make logs      # View container logs
make ps        # List running containers
make backend-logs / make frontend-logs

# Docker 없이 로컬에서 API/프런트만 띄울 때
make backend-local   # uvicorn backend.api.main:app --reload (port 8000)
make frontend-local  # frontend/ 에서 bun run dev (port 3000)
make dev-local       # 위 둘을 동시에 (-j2)
```

### Running Pipelines
파이프라인은 `pipelines/` 최상위 디렉토리에 있다 (`backend/modules/` 아래가 아니다). 새 수집 파이프라인은 `pipelines/<feature>_pipeline.py` 한 파일에 extractor/transformer/loader/pipeline 클래스를 함께 둔다 — 재사용이나 복잡도가 실제로 커졌을 때만 폴더를 분리한다 (`AGENTS.md` 참고).

```python
from pipelines.schedule_to_pdf_pipeline import ScheduleToPDFPipeline
from pipelines.pdf_to_speech_pipeline import PDFToSpeechPipeline
from pipelines.speech_chunk_embedding_pipeline import SpeechChunkEmbeddingPipeline
from pipelines.vectorize_pipeline import VectorizePipeline
from pipelines.contradiction_candidate_pipeline import ContradictionCandidatePipeline
from pipelines.home_snapshot_pipeline import HomeSnapshotPipeline

ScheduleToPDFPipeline(unit_cd="22").run()
```

Docker 컨테이너로 전체 stage를 순서대로 실행할 때는 `pipelines/run_pipeline.py`(= `scripts/run_pipeline.sh`, `make pipeline`)를 쓴다. 기본 stage 순서:

```text
speaker-seed, bill-url-workbook, bill-speech, vectorize, contradiction, home
```

`.env`의 `PIPELINE_STAGES`로 stage를 바꾼다. 새 로컬 DB에 처음부터 데이터를 채울 때는 `make pipeline-bootstrap` (postgres/elasticsearch 기동 → 파이프라인 빌드·실행까지 한 번에).

Airflow가 매일 파이프라인을 스케줄 실행한다 (`airflow/`, `make airflow` / `make airflow-build`). 각 stage는 한 번 재시도 후 최종 실패 시에만 `AIRFLOW_SMTP_*` 설정으로 이메일을 보낸다.

### Backend API
```bash
uv run uvicorn backend.api.main:app --reload
```
FastAPI 앱은 `backend/api/`에 있다 (`main.py`, `routes/api.py`, `services/*.py`). `AGENTS.md`의 최소 DTO 원칙대로, 프런트엔드가 DB 구조를 직접 조립하지 않도록 화면 단위 DTO를 반환한다.

## Architecture

### ETL Pipeline Pattern
`pipelines/base.py`에 공통 추상 클래스가 있다:

- **BaseExtractor**: API/파일에서 원본 데이터 추출
- **BaseTransformer**: 원본 데이터를 구조화된 형태로 변환
- **BaseLoader**: PostgreSQL/Elasticsearch에 적재
- **BasePipeline**: extractor → transformer → loader 흐름 조율

### Main Pipelines (`pipelines/`)

1. **ScheduleToPDFPipeline** / **BillInfoPipeline** / **BillUrlPipeline** — 국회 OpenAPI/워크북에서 회의 일정, 의안 정보, 회의록 PDF URL 수집 (`schedule_to_pdf_pipeline.py`, `bill_collection_pipeline.py`, `utils/openapi.py`)
2. **PDFToSpeechPipeline** — PDF에서 텍스트 추출(pdfplumber) 후 발언 단위로 파싱 (`pdf_to_speech_pipeline.py`)
3. **SpeechChunkEmbeddingPipeline** / **VectorizePipeline** — 발언을 청크로 나누고 sentence-transformers로 임베딩, Elasticsearch/JSONL/FAISS 로더로 적재 (`speech_chunk_embedding_pipeline.py`, `vectorize_pipeline.py`)
4. **ContradictionCandidatePipeline** — 발언 임베딩·메타데이터를 비교해 상반 발언 후보 생성 (제품 핵심 로직, `CONTEXT.md`의 "상반 발언 후보" 정의 참고)
5. **HomeSnapshotPipeline** — 최근 상반 발언 후보를 홈 히어로 DTO로 조립
6. **`speaker_seed.py`** (`uv run python -m pipelines.speaker_seed --load-db`) / **MemberPhotoPipeline** — 의원 기본정보·프로필 사진 데이터 적재

### RAG/Vector Search
- `pipelines/search_service.py` — 발언 검색/유사도 검색 서비스 계층
- 벡터 저장소는 **Elasticsearch** (Qdrant는 더 이상 쓰지 않음)

### LLM Integration
- `pipelines/utils/speech.py` — OpenAI 클라이언트로 발언 요약 생성

## Database Schema

`schema.sql`(레포 루트)이 문서가 아니라 **실제로 실행되는 DDL**이다 (`docs/adr/0002-schema-sql-as-executed-source.md`). 각 Loader의 `create_table()`은 `pipelines/utils/schema.py::load_table_ddl(table)`로 `schema.sql`의 `-- @table: <name>` 섹션을 읽어 그대로 실행한다 — 테이블 정의를 코드에 다시 적지 않는다. 주요 테이블:

- `speakers`, `pdf_url`, `speeches` — 의원, PDF 메타데이터, 발언
- `bill_info`, `bill_url` — 의안 정보와 의안별 회의록 URL
- `contradiction_candidates` — 상반 발언 후보
- `home_section_snapshot` — 홈 화면 히어로 스냅샷
- `pipeline_runs`, `pipeline_row_events` — 파이프라인 실행 이력 (`pipelines/utils/monitoring.py`가 기록)

## Environment Variables

`.env.example`을 `.env`로 복사해 설정한다:

```
POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT
SUPABASE_DATABASE_URL      # 원격 Supabase에 적재할 때만 채움
OPEN_GOVERMENT_API_KEY     # 국회 Open API
OPENAI_API_KEY             # 요약 기능용
AIRFLOW_SMTP_USER, AIRFLOW_SMTP_PASSWORD, PIPELINE_ALERT_EMAIL  # 파이프라인 실패 알림
ELASTICSEARCH_HOST=localhost, ELASTICSEARCH_PORT=9200
PIPELINE_STAGES            # make pipeline 기본 stage를 덮어쓸 때
```

## Key Directories

- `pipelines/` — ETL 파이프라인 코드 (레포 루트, `backend/` 아래가 아님)
  - `base.py` — 공통 추상 클래스
  - `utils/` — `common.py`(공통 예외/설정), `db.py`(DB 연결), `monitoring.py`(실행 이력), `openapi.py`, `speech.py`(요약)
  - `analysis/` — 실험성 분석 보조 스크립트
- `backend/api/` — FastAPI 앱 (`main.py`, `routes/`, `services/`) — 화면 단위 DTO 제공
- `frontend/` — bun 기반 프런트엔드 (자체 `README.md`/`AGENTS.md`/`CLAUDE.md` 보유)
- `airflow/` — 파이프라인 스케줄링 DAG
- `test/` — pytest (flat, `test/unit/` 없음)
- `docs/adr/` — 아키텍처 결정 기록
- `.claude/agents/`, `.claude/skills/` — 7단계 AI 개발 프로세스(플로우 생성 → 검토 → 피쳐 기획 → 검토 → 설계 → 개발 → 검증). "개발 프로세스 시작"이라고 말하면 `dev-process-orchestrator`가 단계를 조율한다.
- `CONTEXT.md` — 프로젝트 용어집 (도메인 용어 + 협업 프로세스 용어)

## gstack

For all web browsing, use the `/browse` skill from gstack. Never use `mcp__claude-in-chrome__*` tools directly.

Available gstack skills:
`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`
