# 배포 계획: 국회 회의록 분석 시스템

## 배경

현재 스택: FastAPI + PostgreSQL + Qdrant + sentence-transformers
- Cloudflare Workers/Pages는 Python FastAPI를 실행할 수 없고, D1은 SQLite 기반이라 PostgreSQL 대체 불가
- Qdrant 벡터DB도 별도 서버 필요

## 추천: Oracle Cloud Free Tier (항상 무료)

- ARM VM 4 OCPU / 24GB RAM **항상 무료** (가장 넉넉한 무료 티어)
- Docker Compose로 전체 스택 배포 가능
- 기존 docker-compose.yaml에 FastAPI 서비스만 추가하면 됨

대안: fly.io (무료 3VM), Render (무료 web service, 비활성시 슬립), Hetzner VPS (€4/월)

---

## 추가/변경된 파일

| 파일 | 설명 |
|------|------|
| `Dockerfile` | FastAPI 앱 컨테이너화 |
| `.dockerignore` | 빌드 최적화 |
| `docker-compose.yaml` | webapp + caddy 서비스 추가, health check |
| `Makefile` | `deploy`, `webapp-logs` 타겟 추가 |
| `Caddyfile` | 리버스 프록시 (자동 HTTPS) |

---

## 배포 절차

```bash
# 1. Oracle Cloud에서 ARM VM 생성 (항상 무료)
# 2. VM에 Docker + Docker Compose 설치
# 3. 프로젝트 클론 & .env 설정
git clone <repo> && cd government_project
cp .env.example .env  # 값 설정

# 4. 배포
make deploy

# 5. 도메인 연결 (선택)
# Caddyfile에서 :80 을 도메인명으로 변경 → 자동 HTTPS
```

## 아키텍처

```
Internet → Caddy (:80/:443) → FastAPI webapp (:8000)
                                  ├── PostgreSQL (:5432)
                                  └── Qdrant (:6333)
```
