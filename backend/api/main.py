from fastapi import FastAPI

from backend.api.config import get_settings
from backend.api.routes import api

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(api.router, prefix="/api", tags=["api"])
