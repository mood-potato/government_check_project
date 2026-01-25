from pathlib import Path

from fastapi.templating import Jinja2Templates

from webapp.services.database import Database
from modules.utils.db_connections import get_qdrant_client
from modules.rag.search_service import SpeechSearchService

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_db():
    """Dependency for database access"""
    return Database()


def get_search_service():
    """Dependency for search service"""
    try:
        client = get_qdrant_client()
        return SpeechSearchService(qdrant_client=client)
    except Exception:
        return None
