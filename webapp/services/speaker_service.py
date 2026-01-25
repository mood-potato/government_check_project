from typing import Any

from webapp.services.database import Database


class SpeakerService:

    @staticmethod
    def get_all(
        name_search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all speakers with stats"""
        query = """
            SELECT
                sp.id,
                sp.name,
                COUNT(s.speech_number) as speech_count,
                COUNT(DISTINCT s.pdf_url_id) as meeting_count,
                MIN(s.date) as first_speech,
                MAX(s.date) as last_speech
            FROM speakers sp
            LEFT JOIN speeches s ON sp.id = s.speaker_id
        """
        params = []

        if name_search:
            query += " WHERE sp.name ILIKE %s"
            params.append(f"%{name_search}%")

        query += """
            GROUP BY sp.id, sp.name
            HAVING COUNT(s.speech_number) > 0
            ORDER BY COUNT(s.speech_number) DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        return Database.fetch_all(query, tuple(params))

    @staticmethod
    def get_by_id(speaker_id: str) -> dict[str, Any] | None:
        """Get speaker by ID"""
        return Database.fetch_one(
            "SELECT id, name FROM speakers WHERE id = %s",
            (speaker_id,),
        )

    @staticmethod
    def get_stats(speaker_id: str) -> dict[str, Any]:
        """Get speaker aggregate statistics"""
        result = Database.fetch_one(
            """
            SELECT
                COUNT(*) as total_speeches,
                COUNT(DISTINCT pdf_url_id) as total_meetings,
                COUNT(DISTINCT class_name) as total_committees,
                AVG(LENGTH(speech)) as avg_speech_length
            FROM speeches
            WHERE speaker_id = %s
            """,
            (speaker_id,),
        )

        return {
            "total_speeches": result["total_speeches"] or 0,
            "total_meetings": result["total_meetings"] or 0,
            "total_committees": result["total_committees"] or 0,
            "avg_speech_length": int(result["avg_speech_length"] or 0),
        }

    @staticmethod
    def get_speeches(
        speaker_id: str,
        class_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get speeches by speaker"""
        query = """
            SELECT
                s.speech_number,
                s.date,
                s.class_name,
                s.speech as text,
                s.summary,
                s.confer_number,
                s.dae_number,
                s.pdf_url_id,
                p.title
            FROM speeches s
            LEFT JOIN pdf_url p ON s.pdf_url_id = p.pdf_url_id::text
            WHERE s.speaker_id = %s
        """
        params = [speaker_id]

        if class_name:
            query += " AND s.class_name = %s"
            params.append(class_name)

        query += " ORDER BY s.date DESC, s.speech_number LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return Database.fetch_all(query, tuple(params))

    @staticmethod
    def get_activity_by_date(speaker_id: str) -> list[dict[str, Any]]:
        """Get daily activity for timeline chart"""
        return Database.fetch_all(
            """
            SELECT date, COUNT(*) as speech_count
            FROM speeches
            WHERE speaker_id = %s
            GROUP BY date
            ORDER BY date
            """,
            (speaker_id,),
        )

    @staticmethod
    def get_top_speakers(limit: int = 20) -> list[dict[str, Any]]:
        """Get top speakers by speech count for chart"""
        return Database.fetch_all(
            """
            SELECT sp.name, COUNT(s.speech_number) as speech_count
            FROM speakers sp
            JOIN speeches s ON sp.id = s.speaker_id
            GROUP BY sp.id, sp.name
            ORDER BY COUNT(s.speech_number) DESC
            LIMIT %s
            """,
            (limit,),
        )
