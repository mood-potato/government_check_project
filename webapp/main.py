from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.config import get_settings
from webapp.routes import home, meetings, speakers, search, api

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

# Static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Template global functions
templates.env.globals["format_number"] = lambda n: f"{n:,}"
templates.env.globals["truncate"] = lambda s, n: s[:n] + "..." if len(s) > n else s

# Include routes
app.include_router(home.router)
app.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
app.include_router(speakers.router, prefix="/speakers", tags=["speakers"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(api.router, prefix="/api", tags=["api"])
