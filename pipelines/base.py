from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from pipelines.utils.monitoring import (
    ensure_monitoring_tables,
    finish_pipeline_run,
    log_load_row_event,
    start_pipeline_run,
)
from pipelines.utils.db import execute_query


class BaseExtractor(ABC):
    """수집기 공통 인터페이스입니다."""

    @abstractmethod
    def extract(self):
        """외부 소스에서 원본 데이터를 수집합니다."""
        pass

    def log_info(self, message: str):
        """수집기 로그 메시지를 남깁니다.

        Args:
            message: 로그에 남길 메시지입니다.
        """
        logger.info(f"[Extractor] {message}")


class BaseTransformer(ABC):
    """변환기 공통 인터페이스입니다."""

    @abstractmethod
    def transform(self, data):
        """원본 데이터를 저장 가능한 형태로 변환합니다.

        Args:
            data: 변환할 원본 데이터입니다.
        """
        pass
    
    def log_info(self, message: str):
        """수집기 로그 메시지를 남깁니다.

        Args:
            message: 로그에 남길 메시지입니다.
        """
        logger.info(f"[Transformer] {message}")


class BasePipeline(ABC):
    """파이프라인 공통 인터페이스입니다."""

    def __init__(self, extractor, loader, transformer=None):
        """파이프라인 구성요소를 초기화합니다.

        Args:
            extractor: 원본 데이터를 수집하는 객체입니다.
            loader: 변환된 데이터를 저장하는 객체입니다.
            transformer: 원본 데이터를 변환하는 객체입니다.
        """
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        self.connection = None
        self.run_id: Optional[str] = None

    @abstractmethod
    def run(self):
        """파이프라인을 실행합니다."""
        pass

    def start_monitoring(
        self,
        pipeline_name: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """파이프라인 실행 모니터링을 시작합니다.

        Args:
            pipeline_name: 파이프라인 이름입니다.
            meta: 실행 설정 메타 정보입니다.

        Returns:
            생성된 run_id 문자열입니다.

        Raises:
            ValueError: connection이 준비되지 않은 경우입니다.
        """
        if self.connection is None:
            raise ValueError("connection이 설정되지 않아 모니터링을 시작할 수 없습니다.")
        ensure_monitoring_tables(self.connection)
        self.run_id = start_pipeline_run(self.connection, pipeline_name, meta)
        return self.run_id

    def finish_monitoring(self, status: str, error_message: Optional[str] = None) -> None:
        """파이프라인 실행 모니터링을 종료합니다.

        Args:
            status: success 또는 failed 상태입니다.
            error_message: 실패 시 에러 메시지입니다.
        """
        if self.connection is None or self.run_id is None:
            return
        finish_pipeline_run(self.connection, self.run_id, status, error_message)


class LoaderError(Exception):
    """로더 처리 중 발생한 오류입니다."""

    pass


class BaseLoader(ABC):
    """저장기 공통 인터페이스입니다."""

    def __init__(self, connection: Any, run_id: Optional[str] = None) -> None:
        """DB 연결을 저장합니다.

        Args:
            connection: 쿼리 실행에 사용할 DB 연결 객체입니다.
            run_id: 파이프라인 실행 ID입니다.
        """
        self.connection = connection
        self.run_id = run_id

    def _execute_query(
        self,
        query: str,
        params: Optional[Union[tuple, dict, List[Union[tuple, dict]]]] = None,
    ) -> Any:
        """DB 쿼리를 실행합니다.

        Args:
            query: 실행할 SQL 문자열입니다.
            params: SQL 파라미터입니다.

        Returns:
            공통 쿼리 실행기가 반환한 결과입니다.

        Raises:
            LoaderError: 쿼리 실행 중 오류가 발생한 경우입니다.
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
        """필요한 DB 테이블을 생성합니다."""
        pass

    @abstractmethod
    def load(self, *args: Any, **kwargs: Any) -> Any:
        """데이터를 저장합니다."""
        pass

    def log_load_row_event(
        self,
        target_table: str,
        record_key: str,
        action: str,
        source_date: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """현재 run_id 기준으로 row 이벤트를 기록합니다.

        Args:
            target_table: 대상 테이블명입니다.
            record_key: 레코드 식별 키입니다.
            action: inserted/updated/skipped/failed 중 하나입니다.
            source_date: 원천 데이터 기준 날짜입니다.
            meta: 추가 메타 정보입니다.
        """
        if not self.run_id:
            return
        log_load_row_event(
            connection=self.connection,
            run_id=self.run_id,
            target_table=target_table,
            record_key=record_key,
            action=action,
            source_date=source_date,
            meta=meta,
        )

    def close(self) -> None:
        """DB 연결을 닫습니다."""
        if hasattr(self, "connection") and self.connection:
            try:
                self.connection.close()
                logger.debug("Database connection closed")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
