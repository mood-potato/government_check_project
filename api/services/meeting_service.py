from typing import Any

from api.services.database import Database


class MeetingService:

    @staticmethod
    def get_stats() -> dict[str, Any]:
        """Get dashboard statistics (4 metrics)"""
        total_meetings = Database.fetch_one(
            "SELECT COUNT(DISTINCT title) as count FROM pdf_url WHERE get_pdf = true"
        )["count"] or 0

        total_speeches = Database.fetch_one(
            "SELECT COUNT(speech_number) as count FROM speeches"
        )["count"] or 0

        total_speakers = Database.fetch_one(
            "SELECT COUNT(*) as count FROM speakers"
        )["count"] or 0

        latest = Database.fetch_one(
            "SELECT MAX(date) as latest FROM pdf_url WHERE get_pdf = true"
        )
        latest_date = latest["latest"].strftime("%Y-%m-%d") if latest["latest"] else "-"

        return {
            "total_meetings": total_meetings,
            "total_speeches": total_speeches,
            "total_speakers": total_speakers,
            "latest_meeting": latest_date,
        }

    @staticmethod
    def get_all(
        class_name: str | None = None,
        dae_number: int | None = None,
        title_search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all meetings with filters"""
        query = """
            SELECT
                p.pdf_url_id,
                p.date,
                p.title,
                p.class_name,
                p.confer_number,
                p.dae_number,
                p.sub_name,
                COUNT(DISTINCT s.speaker_id) as speaker_count,
                COUNT(s.speech_number) as speech_count
            FROM pdf_url p
            LEFT JOIN speeches s ON p.pdf_url_id::text = s.pdf_url_id
            WHERE p.get_pdf = true
        """
        params = []

        if class_name:
            query += " AND p.class_name = %s"
            params.append(class_name)
        if dae_number:
            query += " AND p.dae_number = %s"
            params.append(dae_number)
        if title_search:
            query += " AND p.title ILIKE %s"
            params.append(f"%{title_search}%")

        query += """
            GROUP BY p.pdf_url_id, p.date, p.title, p.class_name,
                     p.confer_number, p.dae_number, p.sub_name
            ORDER BY p.date DESC, p.title
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        return Database.fetch_all(query, tuple(params))

    @staticmethod
    def get_by_id(pdf_url_id: str) -> dict[str, Any] | None:
        """Get single meeting by ID"""
        query = """
            SELECT pdf_url_id, date, title, class_name,
                   confer_number, dae_number, sub_name
            FROM pdf_url WHERE pdf_url_id = %s
        """
        return Database.fetch_one(query, (pdf_url_id,))

    @staticmethod
    def get_speeches(pdf_url_id: str) -> list[dict[str, Any]]:
        """Get speeches for a meeting"""
        query = """
            SELECT
                s.speech_number,
                sp.name as speaker,
                s.speech as text,
                s.summary,
                s.date,
                s.title,
                s.class_name
            FROM speeches s
            JOIN speakers sp ON s.speaker_id = sp.id
            WHERE s.pdf_url_id = %s
            ORDER BY s.speech_number
        """
        return Database.fetch_all(query, (pdf_url_id,))

    @staticmethod
    def get_filter_options() -> dict[str, list]:
        """Get options for filter dropdowns"""
        class_names = Database.fetch_all(
            "SELECT DISTINCT class_name FROM pdf_url WHERE class_name IS NOT NULL ORDER BY class_name"
        )
        dae_numbers = Database.fetch_all(
            "SELECT DISTINCT dae_number FROM pdf_url WHERE dae_number IS NOT NULL ORDER BY dae_number DESC"
        )
        return {
            "class_names": [r["class_name"] for r in class_names],
            "dae_numbers": [r["dae_number"] for r in dae_numbers],
        }
