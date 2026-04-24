# Pipeline Agent Instructions

## External Sources

- 파이프라인 관련 외부 API 정보는 가능한 한 공식 문서나 인터넷 근거를 확인한다.
- 국회 Open API, 공공데이터포털, Supabase, PostgreSQL 등 변경 가능성이 있는 정보는 실행 전에 최신 근거를 확인한다.

## Safe Pipeline Execution

- 실제 적재 검증은 항상 작은 범위로 먼저 실행한다.
- 전체 데이터 실행 전 `page_size`, `max_pages`, `max_workers` 값을 제한한다.
- 실행 전 `.env`의 `OPEN_GOVERMENT_API_KEY`와 `POSTGRES_*` 값이 설정되어 있는지 확인한다.
- 기존 DB 데이터 삭제, 테이블 초기화, 대량 재적재는 명시 요청 없이는 수행하지 않는다.

## Bill Collection Pipeline

- `bill_collection_pipeline.py` 검증 시 기본 범위는 의안 목록 적재와 의안 PDF URL 적재까지다.
- PDF 다운로드, 회의록 텍스트 추출, 벡터화, 분석 파이프라인은 명시 요청 전 실행하지 않는다.
- 제한 실행 예시는 `BillCollectionPipeline`을 직접 import해서 `bill_info_page_size`, `bill_info_max_pages`, `bill_url_page_size`, `bill_url_max_pages`, `bill_url_max_workers`를 작게 지정한다.

## Verification

- 적재 검증은 파이프라인 반환 count와 DB 샘플 조회를 함께 확인한다.
- `bill_info`는 `meeting_id`, `bill_id`, `bill_name`, `detail_link` 샘플을 확인한다.
- `bill_url`은 `agenda_id`, `meeting_id`, `meeting_date`, `download_url`, `get_pdf` 샘플을 확인한다.
- 중복 실행 시 upsert가 정상 동작하는지 확인하되, 기존 `get_pdf` 상태가 의도치 않게 초기화되지 않는지 주의한다.
