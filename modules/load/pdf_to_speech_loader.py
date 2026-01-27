import os
from typing import Dict, List, Optional, Tuple

from loguru import logger

from modules.base.base_loader import BaseLoader


# TODO : pdfurl에서 pdf를 추출하고 상태를 True로 바꾸는 게 중요함
class PDFToSpeechLoader(BaseLoader):
    def __init__(self, connection):
        super().__init__(connection)

    def _create_tables(self) -> None:
        """Create all necessary database tables."""
        try:
            queries = [
                """
                CREATE TABLE IF NOT EXISTS speakers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT NOT NULL UNIQUE,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_speaker UNIQUE (name)
                );
                """,
                """CREATE INDEX IF NOT EXISTS idx_speakers_name ON speakers(name);""",
                """
                CREATE TABLE IF NOT EXISTS speeches (
                    id SERIAL PRIMARY KEY,
                    pdf_url_id TEXT NOT NULL,
                    speaker_id UUID NOT NULL REFERENCES speakers(id) ON DELETE CASCADE,
                    speech_number INT NOT NULL,
                    date DATE NOT NULL,
                    title TEXT,
                    class_name TEXT NOT NULL,
                    confer_number INT NOT NULL,
                    dae_number INT NOT NULL,
                    speech TEXT NOT NULL,
                    summary TEXT,
                    vectorized BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT unique_speech UNIQUE (pdf_url_id, speech_number)
                );
                """,
                """CREATE INDEX IF NOT EXISTS idx_speeches_pdf_url_id ON speeches(pdf_url_id);""",
                """CREATE INDEX IF NOT EXISTS idx_speeches_vectorized ON speeches(vectorized);""",
            ]
            for query in queries:
                self._execute_query(query)

            # 기존 테이블에 새 컬럼 추가 (마이그레이션)
            migration_queries = [
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS id SERIAL;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS title TEXT;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS summary TEXT;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS vectorized BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE speakers ADD COLUMN IF NOT EXISTS title TEXT;",
            ]
            for query in migration_queries:
                try:
                    self._execute_query(query)
                except Exception:
                    pass  # 컬럼이 이미 존재하면 무시

            logger.info("✅ 데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 테이블 생성 실패: {e}")
            raise

    def create_table(self) -> None:
        """Create all necessary database tables."""
        self._create_tables()

    def _save_all_data(self, speech_data: List[Dict]) -> None:
        speakers = {s["speaker"]: s.get("speaker_title") for s in speech_data}
        speaker_map = {}
        speaker_query = """
            INSERT INTO speakers (name, title)
            VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET title = COALESCE(EXCLUDED.title, speakers.title)
            RETURNING id
        """
        for name, title in speakers.items():
            result = self._execute_query(speaker_query, (name, title))
            if result:
                speaker_map[name] = result[0][0]

        speech_query = """
            INSERT INTO speeches (
                pdf_url_id,
                speech_number,
                speaker_id,
                date,
                title,
                class_name,
                confer_number,
                dae_number,
                speech,
                summary,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pdf_url_id, speech_number) DO NOTHING
        """
        for idx, speech in enumerate(speech_data):
            speaker_id = speaker_map.get(speech["speaker"])
            if not speaker_id:
                logger.warning(f"⚠️ 발언자 정보 없음 - {speech['speaker']}")
                continue
            self._execute_query(
                speech_query,
                (
                    speech["pdf_url_id"],
                    idx + 1,
                    speaker_id,
                    speech["date"],
                    speech.get("title"),
                    speech["class_name"],
                    speech["confer_number"],
                    speech["dae_number"],
                    speech["text"],
                    speech.get("summary"),
                    speech["timestamp"],
                ),
            )

    def load(
        self,
        speech_data: List[Dict],
    ) -> None:
        """Save the parsed speech data to PostgreSQL."""
        if not speech_data:
            logger.warning("⚠️ 저장할 발언 데이터가 없습니다.")
            return

        first_speech = speech_data[0]

        # 필수 필드 검증
        required_fields = ("speaker", "text", "timestamp")

        if not all(k in first_speech for k in required_fields):
            logger.error(f"❌ 필수 항목이 누락되었습니다: {required_fields}")
            return

        try:
            # 트랜잭션 시작
            self._execute_query("BEGIN")
            self._save_all_data(speech_data)
            # 트랜잭션 커밋
            self._execute_query("COMMIT")
            logger.info(f"✅ PostgreSQL 저장 완료 - {first_speech['pdf_url_id']}")
        except Exception as e:
            self._execute_query("ROLLBACK")
            logger.error(f"❌ PostgreSQL 저장 실패: {e}")
            raise
