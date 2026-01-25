# Streamlit → FastAPI + Jinja2 Migration Plan

> **Status:** ✅ Completed (2026-01-26)

## Goal
Streamlit 멀티페이지 대시보드를 FastAPI + Jinja2 웹앱으로 마이그레이션

---

## Project Structure

```
webapp/
├── __init__.py
├── main.py                      # FastAPI entry point
├── config.py                    # Settings (pydantic-settings)
├── dependencies.py              # DI (templates, search service)
├── routes/
│   ├── home.py                  # GET /
│   ├── meetings.py              # GET /meetings, /meetings/{id}
│   ├── speakers.py              # GET /speakers, /speakers/{id}
│   ├── search.py                # GET /search
│   └── api.py                   # JSON API endpoints
├── services/
│   ├── database.py              # DB connection wrapper
│   ├── meeting_service.py       # Meeting queries
│   └── speaker_service.py       # Speaker queries
├── templates/
│   ├── base.html                # Tailwind CSS base layout
│   ├── components/              # Reusable components
│   ├── home.html
│   ├── meetings/
│   ├── speakers/
│   └── search.html
└── static/
    ├── css/main.css
    └── js/charts.js             # Plotly.js helpers
```

---

## Tasks

| # | Task | Status |
|---|------|--------|
| 1 | Dependencies 추가 (FastAPI, uvicorn, jinja2, pydantic-settings) | ✅ |
| 2 | Core Application (main.py, config.py, dependencies.py) | ✅ |
| 3 | Service Layer (database, meeting, speaker services) | ✅ |
| 4 | Routes (home, meetings, speakers, search, api) | ✅ |
| 5 | Templates (base + 8개 페이지, Tailwind CSS) | ✅ |
| 6 | Static Files (CSS, Plotly.js charts) | ✅ |
| 7 | Tests (15개 unit tests) | ✅ |
| 8 | Git Commit | ✅ |

---

## Tech Stack

- **Backend:** FastAPI 0.115+
- **Templates:** Jinja2
- **CSS:** Tailwind CSS (CDN)
- **Charts:** Plotly.js (client-side)
- **Font:** Pretendard (Korean)
- **Database:** PostgreSQL (psycopg2)
- **Vector Search:** Qdrant (reusing modules/rag/search_service.py)

---

## URL Mapping

| Route | Description |
|-------|-------------|
| `GET /` | Home dashboard with stats |
| `GET /meetings` | Meeting list (filters: committee, session, q) |
| `GET /meetings/{id}` | Meeting detail with speeches |
| `GET /speakers` | Speaker list (filter: q) |
| `GET /speakers/{id}` | Speaker detail with activity |
| `GET /search` | Semantic search |
| `GET /api/stats` | JSON: Dashboard stats |
| `GET /api/meetings` | JSON: Meetings list |
| `GET /api/speakers` | JSON: Speakers list |
| `POST /api/search` | JSON: Search results |

---

## Verification

```bash
# Run webapp
uv run uvicorn webapp.main:app --reload --port 8000

# Run tests
uv run pytest test/unit/test_webapp/ -v
```

---

## Commits

1. `a498c5d` ✨ Add: FastAPI + Jinja2 webapp replacing Streamlit
2. `9ca6962` 🔥 Remove: 기존 Streamlit 앱 삭제
