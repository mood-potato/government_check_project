from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

from loguru import logger

from backend.modules.utils.db_helpers import execute_query


class LoaderError(Exception):
    """Base exception for loader related errors"""

    pass


class BaseLoader(ABC):
    """Base class for all data loaders."""

    def __init__(self, connection: Any) -> None:
        """Initialize the loader with a database connection.

        Args:
            connection: A database connection object.
        """
        self.connection = connection

    def _execute_query(
        self,
        query: str,
        params: Optional[Union[tuple, dict, List[Union[tuple, dict]]]] = None,
    ) -> Any:
        """Execute a database query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result

        Raises:
            LoaderError: If query execution fails
        """
        try:
            logger.debug(f"Executing query: {query}")
            if params:
                logger.debug(f"With params: {params}")
            return execute_query(self.connection, query, params)
        except Exception as e:
            error_msg = f"Query execution failed: {str(e)}"
            logger.error(error_msg)
            raise LoaderError(error_msg) from e
    
    @abstractmethod
    def create_table(self):
        """Create necessary database tables."""
        pass

    @abstractmethod
    def load(self, *args: Any, **kwargs: Any) -> Any:
        """Load data. To be implemented by subclasses."""
        pass

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, "connection") and self.connection:
            try:
                self.connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")


