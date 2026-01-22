import datetime
import re
from typing import Dict, List, Optional

from loguru import logger

from modules.base.base_transformer import BaseTransformer


class PDFToSpeechTransformer(BaseTransformer):
    """
    국회 회의록 PDF에서 발언 텍스트를 파싱하여 구조화된 리스트로 반환하는 클래스
    """

    def __init__(self, enable_summary: bool = False):
        """
        Args:
            enable_summary: True면 LLM 요약 기능 활성화
        """
        # 발언자 패턴 정의: ◯홍길동\n 발언내용
        self.speaker_pattern = re.compile(
            r"◯([\w]+ [\w]+)\s*\n*([\s\S]+?)(?=\n◯|\Z)", re.MULTILINE
        )
        self.enable_summary = enable_summary
        self.summarizer: Optional["SpeechSummarizer"] = None

        if enable_summary:
            try:
                from modules.llm.summarizer import SpeechSummarizer
                self.summarizer = SpeechSummarizer()
                if self.summarizer.is_available():
                    logger.info("요약 기능이 활성화되었습니다.")
                else:
                    logger.warning("OPENAI_API_KEY가 없어 요약 기능이 비활성화됩니다.")
                    self.summarizer = None
            except ImportError as e:
                logger.warning(f"요약 모듈 로드 실패: {e}")
                self.summarizer = None

    def transform(
        self,
        pdf_url_id: str,
        text: str,
        title: str,
        date: str,
        confer_number: str,
        dae_number: str,
        class_name: str,
        file_path: str,
    ) -> List[Dict]:
        """
        전체 회의록 텍스트에서 발언 정보를 파싱

        Args:
            pdf_url_id (str): PDF URL ID
            text (str): 전체 회의록 텍스트
            title (str): 회의록 제목
            date (str): 회의일
            confer_number (str): 회의번호
            dae_number (str): 대수
            class_name (str): 위원회 종류
            file_path (str): PDF URL

        Returns:
            List[dict]: 발언 데이터가 담긴 딕셔너리 리스트
        """
        speech_list = []

        for idx, match in enumerate(self.speaker_pattern.finditer(text), start=1):
            speaker = match.group(1).strip()
            speech = match.group(2).strip()

            # 요약 생성 (활성화된 경우)
            summary = None
            if self.summarizer:
                summary = self.summarizer.summarize(speech)

            speech_list.append(
                {
                    "pdf_url_id": pdf_url_id,
                    "title": title,
                    "date": date,
                    "confer_number": confer_number,
                    "dae_number": dae_number,
                    "class_name": class_name,
                    "speaker": speaker,
                    "speech_number": idx,
                    "text": speech,
                    "summary": summary,
                    "timestamp": datetime.datetime.now(),
                    "file_path": file_path,
                }
            )

        return speech_list
