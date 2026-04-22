from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Dict, List, Optional

import pdfplumber
import httpx

from pipelines.base.base_extractor import BaseExtractor
from pipelines.utils.db_helpers import update_get_pdf_status


class PDFToSpeechExtractor(BaseExtractor):
    """PDF URL 처리 및 텍스트 추출 + DB 연동"""

    def __init__(
        self,
        pdf_url: Optional[str] = None,
        title: Optional[str] = None,
        date: Optional[str] = None,
        connection=None,
    ):
        self.pdf_url: Optional[str] = pdf_url
        self.title: Optional[str] = title
        self.date: Optional[str] = date
        self.connection = connection

    def fetch_pdf_urls(self) -> List[Dict[str, str]]:
        """Unprocessed PDF URL List"""
        if self.connection is None:
            raise ValueError("DB connection is not provided.")

        query: str = """
            SELECT pdf_url_id, pdf_url, title, date, confer_number, dae_number, class_name
            FROM pdf_url
            WHERE get_pdf = false
        """
        with self.connection.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return [dict(zip([col.name for col in cur.description], row)) for row in rows]

    def extract_one(self, row: Dict[str, str]) -> Dict[str, str]:
        pdf_url_id = row.get("pdf_url_id")
        pdf_url = row.get("pdf_url")
        title = row.get("title")
        date = row.get("date")
        confer_number = row.get("confer_number")
        dae_number = row.get("dae_number")
        class_name = row.get("class_name")        

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(pdf_url)
                response.raise_for_status()
                with pdfplumber.open(BytesIO(response.content)) as pdf:
                    text = "\n".join(
                        page.extract_text() for page in pdf.pages if page.extract_text()
                    )
            self.log_info(f"✅ 처리 완료: {title}")
            return {
                "pdf_url_id": pdf_url_id,
                "title": title,
                "date": date,
                "text": text,
                "confer_number": confer_number,
                "dae_number": dae_number,
                "class_name": class_name,
                "file_path": pdf_url,
            }
        except Exception as e:
            self.log_info(f"❌ {title} PDF 처리 실패: {e}")
            update_get_pdf_status(self.connection, pdf_url_id, False)
            raise

    def extract_all(self, max_workers: int = 10) -> List[Dict[str, str]]:
        rows = self.fetch_pdf_urls()
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.extract_one, row) for row in rows]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        return results

    def extract(self) -> List[dict]:
        """
        PDF URL 목록을 병렬로 처리하고, 텍스트를 추출합니다.
        """
        return self.extract_all()
