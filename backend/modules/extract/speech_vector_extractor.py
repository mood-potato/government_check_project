from typing import Any, Dict, List

from loguru import logger

from backend.modules.base.base_extractor import BaseExtractor


class SpeechVectorExtractor(BaseExtractor):
    """벡터화되지 않은 speeches 추출"""

    def __init__(self, connection: Any, batch_size: int = 1000):
        self.connection = connection
        self.batch_size = batch_size

    def extract(self) -> List[Dict]:
        """벡터화되지 않은 발언 데이터 추출"""
        query = """
            SELECT s.id, s.speech as text, sp.name as speaker, s.date, s.title
            FROM speeches s
            LEFT JOIN speakers sp ON s.speaker_id = sp.id
            WHERE s.vectorized = false OR s.vectorized IS NULL
            LIMIT %s
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(query, (self.batch_size,))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                self.log_info(f"벡터화 대상 {len(results)}건 추출 완료")
                return results
        except Exception as e:
            logger.error(f"발언 추출 중 오류: {e}")
            return []

    def mark_as_vectorized(self, speech_ids: List[int]) -> None:
        """벡터화 완료된 발언 상태 업데이트"""
        if not speech_ids:
            return

        query = "UPDATE speeches SET vectorized = true WHERE id = ANY(%s)"
        try:
            with self.connection.cursor() as cur:
                cur.execute(query, (speech_ids,))
                self.connection.commit()
                logger.info(f"{len(speech_ids)}건 벡터화 상태 업데이트 완료")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"벡터화 상태 업데이트 실패: {e}")
