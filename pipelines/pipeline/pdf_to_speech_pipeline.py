from loguru import logger

from pipelines.base.base_pipeline import BasePipeline
from pipelines.extract.pdf_to_speech_extractor import PDFToSpeechExtractor
from pipelines.load.pdf_to_speech_loader import PDFToSpeechLoader
from pipelines.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
from pipelines.utils.db_connections import get_postgres_connection
from pipelines.utils.db_helpers import update_get_pdf_status


class PDFToSpeechPipeline(BasePipeline):
    def __init__(self):
        connection = get_postgres_connection()
        self.connection = connection
        extractor = PDFToSpeechExtractor(connection=connection)
        loader = PDFToSpeechLoader(connection=connection)
        transformer = PDFToSpeechTransformer()
        super().__init__(extractor, loader, transformer)

    def run(self):
        logger.info("✅ 병렬로 PDF 추출 시작")
        raw_data = self.extractor.extract()
        logger.info(f"✅ 처리 완료: 총 {len(raw_data)}건")

        for item in raw_data:
            logger.info(f"\n{item['title']} ({item['date']})")

            transformed_result = self.transformer.transform(
                text=item["text"],
                title=item["title"],
                date=item["date"],
                class_name=item["class_name"],
                file_path=item["file_path"],
                confer_number=item["confer_number"],
                dae_number=item["dae_number"],
                pdf_url_id=item["pdf_url_id"],
            )

            logger.info(f"추출된 발언 수: {len(transformed_result)}")
            for speech in transformed_result[:3]:
                logger.info(f"- {speech['speaker']}: {speech['text'][:100]}...")

            if not transformed_result:
                logger.warning("⚠️ 변환된 발언이 없어 건너뜁니다.")
                continue

            try:
                self.loader.load(speech_data=transformed_result)
                logger.info(f"✅ DB 저장 완료: {len(transformed_result)}건")
                update_get_pdf_status(self.connection, item["pdf_url_id"], True)
            except Exception as e:
                update_get_pdf_status(self.connection, item["pdf_url_id"], False)
                logger.error(f"❌ DB 저장 중 오류 발생: {e}")
