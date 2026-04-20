from backend.api.services.database import Database
from backend.modules.utils.db_connections import get_elasticsearch_client
from backend.modules.search.search_service import SpeechSearchService


def get_db():
    """Dependency for database access"""
    return Database()


def get_search_service():
    """Dependency for search service"""
    try:
        client = get_elasticsearch_client()
        return SpeechSearchService(client=client)
    except Exception:
        return None
