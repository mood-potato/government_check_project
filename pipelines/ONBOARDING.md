# Pipelines Onboarding Guide

이 가이드는 `pipelines/.understand-anything/knowledge-graph.json`을 근거로 작성했습니다.

## Project Overview

`government-check-project pipelines`는 국회의원 회의록, 의안, 의원 프로필, 발언 청크와 임베딩, 상반 발언 후보를 수집, 변환, 적재하는 Python 파이프라인 영역입니다.

- Languages: Python, Markdown
- Frameworks/Infra: Python, PostgreSQL/Supabase, OpenAI API
- 주요 근거: 프로젝트 README의 회의록 분석 서비스 설명, `pyproject.toml`의 `httpx`, `pandas`, `pdfplumber`, `psycopg2`, `openai`, `sentence-transformers` 의존성

## Architecture Layers

### 공통 기반

- 핵심 파일: `base.py`, `utils/common.py`, `__init__.py`
- Extractor, Transformer, Loader, Pipeline 공통 계약과 공통 예외를 정의합니다.

### 외부 데이터 수집

- 핵심 파일: `schedule_to_pdf_pipeline.py`, `bill_collection_pipeline.py`, `utils/openapi.py`
- 국회 OpenAPI, 회의 일정, 의안 정보, PDF URL, 워크북 원천 데이터를 수집합니다.

### 발언 추출과 벡터화

- 핵심 파일: `pdf_to_speech_pipeline.py`, `speech_chunk_embedding_pipeline.py`, `vectorize_pipeline.py`, `search_service.py`
- 회의록 PDF를 발언 데이터로 바꾸고, 발언 청크를 임베딩 및 검색 인덱스로 연결합니다.

### 상반 후보와 홈 스냅샷

- 핵심 파일: `contradiction_candidate_pipeline.py`, `home_snapshot_pipeline.py`
- 상반 발언 후보를 만들고 홈 화면 히어로 DTO로 조립합니다.

### 의원 프로필 데이터

- 핵심 파일: `speaker_seed.py`, `member_photo_pipeline.py`
- 의원 기본정보, seed SQL, 프로필 사진 데이터를 준비합니다.

### 운영 유틸리티와 분석 보조

- 핵심 파일: `utils/db.py`, `utils/monitoring.py`, `utils/speech.py`, `analysis/*`, `AGENTS.md`
- DB 연결, 실행 모니터링, 요약, 실험성 분석 스크립트, 작업 지침을 담당합니다.

## Key Concepts

- 파이프라인은 `Extractor -> Transformer -> Loader -> Pipeline` 흐름으로 읽는 것이 가장 빠릅니다.
- 외부 출처 기반 데이터가 많으므로 `AGENTS.md`의 근거와 원문 확인 기준을 우선합니다.
- DB 접근은 `utils/db.py`, 실행 이력은 `utils/monitoring.py`로 모입니다.
- 제품 방향상 `모순`보다 `상반 발언 후보`, `자동 분석`, `원문 확인` 같은 중립 표현을 유지해야 합니다.
- 홈 화면 관련 데이터는 `contradiction_candidate_pipeline.py`에서 후보를 만들고 `home_snapshot_pipeline.py`에서 표시용 DTO로 정리됩니다.

## Guided Tour

1. `AGENTS.md`, `base.py`
   - 작업 지침, 공통 실행 계약, 모니터링 흐름을 먼저 확인합니다.

2. `schedule_to_pdf_pipeline.py`, `bill_collection_pipeline.py`, `utils/openapi.py`
   - 회의 일정, 의안 정보, PDF URL 수집 흐름을 따라갑니다.

3. `pdf_to_speech_pipeline.py`, `utils/db.py`
   - PDF 또는 URL에서 발언 텍스트를 추출하고 저장하는 단계를 봅니다.

4. `speech_chunk_embedding_pipeline.py`, `vectorize_pipeline.py`, `search_service.py`
   - 발언 청크, 임베딩, Elasticsearch 검색 흐름을 확인합니다.

5. `contradiction_candidate_pipeline.py`, `home_snapshot_pipeline.py`
   - 상반 발언 후보 생성과 홈 히어로 스냅샷 조립 방식을 봅니다.

6. `speaker_seed.py`, `member_photo_pipeline.py`
   - 의원 프로필 기반 데이터 적재 흐름을 확인합니다.

7. `utils/monitoring.py`, `utils/speech.py`, `analysis/query_speak.py`, `analysis/summary_meeting_speak.py`
   - 운영 기록, 요약, 분석 보조 스크립트를 봅니다.

## File Map

### 공통 기반

- `base.py`: Extractor, transformer, loader, pipeline의 공통 실행 계약과 모니터링 훅을 정의합니다.
- `utils/common.py`: 공통 예외와 공통 설정값을 제공합니다.
- `__init__.py`: `pipelines` 패키지 초기화 파일입니다.

### 외부 데이터 수집

- `schedule_to_pdf_pipeline.py`: 국회 회의 일정과 회의록 PDF URL을 수집하고 후속 파이프라인 입력으로 저장합니다.
- `bill_collection_pipeline.py`: 국회 의안 정보와 의안별 회의록 URL을 OpenAPI 또는 워크북에서 수집해 데이터베이스에 적재합니다.
- `utils/openapi.py`: 국회 OpenAPI 페이지네이션 요청, 기존 수집 데이터 조회, 날짜 필터 생성을 담당합니다.

### 발언 추출과 벡터화

- `pdf_to_speech_pipeline.py`: 회의록 PDF 또는 URL에서 발언 텍스트를 추출하고 발언 단위 데이터로 변환해 저장합니다.
- `speech_chunk_embedding_pipeline.py`: 발언 텍스트를 청크로 나누고 임베딩한 뒤 Elasticsearch, JSONL, FAISS 로더로 적재합니다.
- `vectorize_pipeline.py`: 기존 발언 데이터를 벡터화하고 Elasticsearch에 색인합니다.
- `search_service.py`: 발언 검색과 유사도 검색을 서비스 계층에서 호출할 수 있게 감쌉니다.

### 상반 후보와 홈 스냅샷

- `contradiction_candidate_pipeline.py`: 발언 임베딩과 메타데이터를 비교해 상반 발언 후보를 자동 분석 대상으로 생성합니다.
- `home_snapshot_pipeline.py`: 최근 상반 발언 후보를 홈 화면 히어로 DTO로 렌더링할 수 있게 스냅샷 형태로 조립합니다.

### 의원 프로필 데이터

- `speaker_seed.py`: 국회의원 CSV 원천 데이터를 `speakers` 테이블 seed SQL 또는 원격 데이터베이스 적재 데이터로 변환합니다.
- `member_photo_pipeline.py`: 국회의원 프로필 사진과 기본 정보를 정리해 인물 중심 화면에서 사용할 수 있게 적재합니다.

### 운영 유틸리티와 분석 보조

- `utils/db.py`: PostgreSQL과 Elasticsearch 연결 및 공통 쿼리 실행을 담당합니다.
- `utils/monitoring.py`: 파이프라인 실행 기록, row 단위 적재 이벤트, 완료 상태를 데이터베이스에 기록합니다.
- `utils/speech.py`: OpenAI 클라이언트를 이용해 발언 요약을 생성합니다.
- `analysis/query_speak.py`: 발언 검색과 조회를 실험적으로 확인하는 분석 보조 스크립트입니다.
- `analysis/summary_meeting_speak.py`: 회의 발언 요약을 실험적으로 생성하는 분석 보조 스크립트입니다.
- `analysis/get_api_module.py`: API 호출 관련 실험성 보조 모듈입니다.
- `analysis/get_all_speark.py`: 분석 디렉터리에 포함된 보조 파일입니다.
- `AGENTS.md`: 파이프라인 작업 시 외부 출처 근거, 안전한 실행, 검증 기준을 설명하는 지침 문서입니다.

## Complexity Hotspots

- `bill_collection_pipeline.py`: complex
  - 의안 정보, 의안별 회의록 URL, OpenAPI, 워크북 처리가 함께 있어 변경 전 테스트 범위를 넓게 잡아야 합니다.
- `pdf_to_speech_pipeline.py`: complex
  - PDF 처리, 로컬/URL 입력, 발언 변환, 적재 상태 갱신이 얽혀 있습니다.
- `speech_chunk_embedding_pipeline.py`: complex
  - 청크 분할, 임베딩, Elasticsearch/JSONL/FAISS 로더가 함께 움직입니다.
- `contradiction_candidate_pipeline.py`: complex
  - 제품 핵심인 상반 발언 후보 생성 로직이므로 표현 안전성과 근거 데이터 확인이 중요합니다.
- `speaker_seed.py`: complex
  - CSV 원천 데이터를 DB seed/적재 형태로 바꾸므로 필드 정규화와 날짜/숫자 파싱을 주의해야 합니다.
