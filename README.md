# goverment_check_project
국회의원 회의록 분석 확인하는 웹사이트

## 국회의원 회의록 분석
- 국회의원 안건 의견 비교

## Docker

```bash
make up
make logs
make down
```

- 백엔드: `docker/backend.Dockerfile`
- 프론트엔드: `docker/frontend.Dockerfile`
- 파이프라인: `docker/pipeline.Dockerfile`

파이프라인은 필요할 때만 실행합니다.

```bash
make pipeline
```

## Supabase 데이터 적재

Supabase는 PostgreSQL 연결 문자열로 적재합니다. Supabase 문서 기준으로
프런트엔드는 Data API를 쓰지만, 파이프라인 같은 Postgres 클라이언트는 연결 문자열을
사용합니다. IPv4 환경에서는 Supavisor Session pooler 문자열을 쓰는 것이 안전합니다.

`.env`에 다음 값을 설정하면 기존 파이프라인과 seed 로더가 원격 Supabase DB를 우선
사용합니다.

```bash
SUPABASE_DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres
```

의원 기본정보 CSV를 `speakers` 테이블에 직접 적재합니다.

```bash
uv run python -m pipelines.speaker_seed --load-db
```

회의록 PDF URL 수집, 발언 추출, 벡터화를 순서대로 실행합니다.

```bash
make pipeline
```
