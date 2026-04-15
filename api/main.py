from fastapi import FastAPI

from api.config import get_settings
from api.routes import api

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(api.router, prefix="/api", tags=["api"])
