# Onboarding

새로 이 레포에 들어온 사람(사람이든 Claude Code든)이 확인할 순서. 각 단계는 실제로 실행해서 검증한 명령이다.

## 1. 문서 읽기 순서

1. `README.md` — 프로젝트 개요, Docker 명령
2. `AGENTS.md` — 제품 방향, 코드 스타일, 파이프라인 파일 구조 규칙
3. `CLAUDE.md` — Claude Code용 아키텍처 요약 (pipelines/, backend/api, frontend)
4. `CONTEXT.md` — 용어집 (제품 도메인 + 협업 프로세스)
5. 하위 디렉토리별 `AGENTS.md`(`pipelines/`, `frontend/`, `supabase/`) — 그 디렉토리에서 작업할 때만

## 2. 로컬 환경

```bash
cp .env.example .env
uv sync
```

`.env`에 필요한 값(`OPEN_GOVERMENT_API_KEY`, `OPENAI_API_KEY`, `SUPABASE_DATABASE_URL` 등)은 아직 팀 공유 방법이 정해지지 않았다 — 실제 팀원이 생기면 그때 정한다.

## 3. 인프라 기동 확인

```bash
make up
make ps   # postgres, elasticsearch, backend, frontend, pipeline, airflow, caddy 순서로 healthy 확인
```

## 4. 테스트로 확인

컨테이너가 호스트에 포트를 공개하므로, 컨테이너 밖(호스트)에서 직접 실행할 때는 `POSTGRES_HOST`를 `localhost`로 덮어써야 한다 (`.env.example`의 기본값 `postgres`는 Docker 네트워크 안에서만 resolve된다).

```bash
POSTGRES_HOST=localhost ELASTICSEARCH_HOST=localhost uv run pytest
```

88 passed 기준으로 검증됨 (2026-08-02).

## 5. 데이터 채우기 (필요할 때만)

```bash
make pipeline-bootstrap
```

국회 Open API를 실제로 호출하므로 처음 한 번만, 필요할 때만 실행한다.

## 6. 로컬 개발 서버

```bash
make dev-local   # backend :8000 + frontend :3000 동시 기동
```

## 7. AI 개발 프로세스

Claude Code 세션에서 "개발 프로세스 시작"이라고 말하면 `dev-process-orchestrator`가 7단계(플로우 생성 → 검토 → 피쳐 기획 → 검토 → 설계 → 개발 → 검증)를 조율한다. `.claude/agents`, `.claude/skills`는 git에 커밋되어 있어 clone만으로 동일하게 사용 가능하다.

## 아직 안 된 것

- `.env` 시크릿(API 키, DB 접속정보)을 실제 팀원과 공유하는 방법 — 실제 팀원이 생기면 결정
- Notion 워크스페이스가 개인용인지 팀용인지 — `notion-save` 스킬로 팀 공유하려면 팀 워크스페이스 이관 필요
