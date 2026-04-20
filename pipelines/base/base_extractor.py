from abc import ABC, abstractmethod

from loguru import logger


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self):
        pass

    def log_info(self, message: str):
        logger.info(f"[Extractor] {message}")
