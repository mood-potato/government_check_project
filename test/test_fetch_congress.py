from modules.utils.url_constants import (
    MAIN_CONGRESS_SCHEDULE_URL,
    MAIN_CONGRESS_SPEECH_PDF_URL,
)
from modules.extract.congress_schedule_extractor import CongressScheduleExtractor
from modules.extract.pdf_url_extractor import PDFUrlExtractor
from modules.transform.congress_schedule_transformer import CongressScheduleTransformer
from modules.transform.pdf_url_transformer import PDFUrlTransformer
from modules.load.pdf_url_loader import PDFUrlLoader
from modules.utils.db_connections import get_postgres_connection

if __name__ == "__main__":
    # Step 1: 일정 추출
    schedule_extractor = CongressScheduleExtractor(url=MAIN_CONGRESS_SCHEDULE_URL)
    print("✅ 일정 extractor 시작")
    schedule_data = schedule_extractor.extract()
    print("✅ 일정 데이터 추출 완료")
    
    # Step 2: 날짜 리스트 생성
    meeting_dates = CongressScheduleTransformer().transform(schedule_data)
    print(f"✅ 날짜 리스트 생성 완료 ({len(meeting_dates)}건)")

    # Step 3: PDF URL 추출
    pdf_extractor = PDFUrlExtractor(
        url=MAIN_CONGRESS_SPEECH_PDF_URL, meeting_dates=meeting_dates, unit_cd="22"
    )

    print("✅ PDF extractor 시작")
    pdf_data, fetched_dates = pdf_extractor.extract()
    print(f"✅ PDF 데이터 추출 완료 ({len(pdf_data)}건)")
    transformed_pdf_data = PDFUrlTransformer().transform(pdf_data)
    print(f"✅ PDF 데이터 변환 완료 ({len(transformed_pdf_data)}건)")

    # Step 4: PostgreSQL 저장
    connection = get_postgres_connection()
    pdf_url_loader = PDFUrlLoader(connection)
    pdf_url_loader.create_table()

    for item in transformed_pdf_data:
        pdf_url_data = {
            "CONFER_NUM": item.get("CONFER_NUM"),
            "DAE_NUM": item.get("DAE_NUM"),
            "CONF_DATE": item.get("CONF_DATE"),
            "TITLE": item.get("TITLE"),
            "CLASS_NAME": item.get("CLASS_NAME"),
            "SUB_NAME": item.get("SUB_NAME"),
            "VOD_LINK_URL": item.get("VOD_LINK_URL"),
            "CONF_LINK_URL": item.get("CONF_LINK_URL"),
            "PDF_LINK_URL": item.get("PDF_LINK_URL"),
            "get_pdf": False,
        }
        pdf_url_loader.load(pdf_url_data)

    connection.close()
    print("✅ PostgreSQL 저장 완료")

