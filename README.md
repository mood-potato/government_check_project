# goverment_check_project
국회의원 회의록 분석 확인하는 웹사이트


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

새 로컬 DB를 만들고 포함된 데이터로 기본 파이프라인을 처음부터 돌릴 때는 다음 명령을
사용합니다.

```bash
cp .env.example .env
make pipeline-bootstrap
```

`pipeline-bootstrap`은 Postgres와 Elasticsearch를 먼저 띄운 뒤 파이프라인 컨테이너를
빌드하고 실행합니다. 기본 stage는 다음 순서입니다.

```text
speaker-seed,bill-url-workbook,bill-speech,vectorize,contradiction,home
```

실행 stage를 바꾸려면 `.env`의 `PIPELINE_STAGES`를 수정하거나 명령 앞에 환경변수를
붙입니다.

```bash
PIPELINE_STAGES=speaker-seed,bill-info,bill-url,bill-speech,vectorize,contradiction,home make pipeline
```

SSH 서버나 로컬 PC에서 Make 없이 직접 실행하려면 스크립트를 사용합니다.

```bash
scripts/run_pipeline.sh --build
scripts/run_pipeline.sh --stages bill-speech
```

Postgres와 Elasticsearch 볼륨까지 지우고 완전히 새로 검증할 때만 `--reset`을 붙입니다.

```bash
scripts/run_pipeline.sh --reset --build
```

이 스크립트는 기본적으로 `SUPABASE_DATABASE_URL`을 비워서 Docker Compose의 로컬
Postgres에 적재합니다. 원격 Supabase에 적재할 때만 명시적으로 `--use-supabase`를
붙입니다.

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
