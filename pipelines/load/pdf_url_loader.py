from loguru import logger
from pipelines.base.base_loader import BaseLoader


class PDFUrlLoader(BaseLoader):
    """
    PDF URL 데이터를 저장하는 클래스
    
    Args:
        loader (BaseLoader): BaseLoader 인스턴스
    
    """
    def __init__(self, connection):
        super().__init__(connection)

    def create_table(self):
        query = """
            CREATE TABLE IF NOT EXISTS pdf_url (
                pdf_url_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                confer_number INT,
                dae_number INT,
                date DATE NOT NULL,
                title TEXT NOT NULL,
                class_name TEXT,
                sub_name TEXT,
                vod_link TEXT,
                conf_link TEXT,
                pdf_url TEXT,
                get_pdf BOOLEAN DEFAULT FALSE,
                CONSTRAINT unique_pdf UNIQUE (date, title, pdf_url)
            );
        """
        self._execute_query(query)
        logger.info("✅ pdf_url 테이블 생성 완료 (또는 이미 존재함)")

    def load(self, pdf_url_data):
        try:
            logger.info(
                f"➕ PDF URL 삽입 시도: {pdf_url_data.get('date')} - {pdf_url_data.get('sub_name')}"
            )
            query = """
                INSERT INTO pdf_url (
                    confer_number, dae_number, date, title, class_name,
                    sub_name, vod_link, conf_link, pdf_url, get_pdf
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (date, title, pdf_url) DO NOTHING;
            """
            params = (
                pdf_url_data.get("CONFER_NUM"),
                pdf_url_data.get("DAE_NUM"),
                pdf_url_data.get("CONF_DATE"),
                pdf_url_data.get("TITLE"),
                pdf_url_data.get("CLASS_NAME"),
                pdf_url_data.get("SUB_NAME"),
                pdf_url_data.get("VOD_LINK_URL"),
                pdf_url_data.get("CONF_LINK_URL"),
                pdf_url_data.get("PDF_LINK_URL"),
                pdf_url_data.get("get_pdf", False),
            )
            result = self._execute_query(query, params)
            if result is not None:
                logger.debug(f"Query result: {result}")
            logger.success(f"✅ PDF URL 저장 성공: {pdf_url_data.get('date')} - {pdf_url_data.get('sub_name')}")
        except Exception as e:
            logger.error(f"❌ PDF URL 저장 중 오류 발생: {str(e)}")
            raise