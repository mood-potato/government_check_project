# schema.sql을 실제로 실행되는 DDL 소스로 만든다

DB 스키마 정의가 `schema.sql`(문서, 아무 코드도 실행 안 함), 7개 파이프라인 파일에 흩어진 `CREATE TABLE` 문(실제 로컬 Postgres를 만드는 코드), `supabase/migrations/`(원격 Supabase 전용) 세 곳으로 나뉘어 있었고, 실제로 서로 어긋나 있었다 (`pdf_url`의 `created_at`/`updated_at`처럼 문서에만 있는 컬럼, `idx_speeches_recent_member`처럼 migration에만 있고 로컬엔 없는 인덱스, `speakers` 테이블은 아예 어떤 파이썬 코드도 만들지 않아 완전히 새 DB에서는 첫 파이프라인 단계부터 실패하는 문제까지 있었다).

각 Loader가 자기 SQL을 따로 적는 대신 `schema.sql`을 유일한 소스로 삼기로 했다. `pipelines/utils/schema.py::load_table_ddl(table)`이 `schema.sql`의 `-- @table: <name>` 마커로 구분된 섹션을 읽어 그대로 반환하고, 각 Loader의 `create_table()`은 그 텍스트를 실행만 한다. 모든 문장이 `IF NOT EXISTS` 기반이라 여러 Loader가 같은 파일을 반복 실행해도 안전하다.

기존 컬럼/인덱스 중 실제로 쓰이지 않는 것(`pdf_url.created_at`/`updated_at` 등)은 코드 쪽 실제 모습에 맞춰 문서에서 뺐고, 반대로 코드에는 없었지만 실제로 존재하던 것(`bill_info`/`bill_url`의 추가 인덱스, `idx_speeches_recent_member`/`idx_speeches_speaker_date_order`)은 `schema.sql`에 넣고 로컬에서도 실제로 생성되도록 코드에 반영했다. 이미 배포된 DB를 깨뜨릴 수 있는 컬럼 타입 변경(`speeches.created_at`의 `TIMESTAMP` vs `TIMESTAMPTZ`)이나 `NOT NULL` 강제는 하지 않고 현재 실제 동작을 그대로 문서화했다.
