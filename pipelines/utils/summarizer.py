import os
from typing import List, Optional

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

load_dotenv()


class SpeechSummarizer:
    """국회 발언 요약 서비스"""

    SYSTEM_PROMPT = """당신은 국회 회의록 분석 전문가입니다.
주어진 발언을 핵심 내용 중심으로 2-3문장으로 요약하세요.

요약 규칙:
- 발언자의 주장과 근거를 명확히 포함
- 구체적인 수치나 법안명이 있으면 유지
- 중립적인 어조 유지
- 한국어로 작성"""

    def __init__(self, model: str = "gpt-4o-mini", min_length: int = 100):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 요약 기능이 비활성화됩니다.")
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key)

        self.model = model
        self.min_length = min_length

    def summarize(self, text: str) -> Optional[str]:
        if not self.client:
            return None

        if len(text) < self.min_length:
            return text

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"다음 발언을 요약하세요:\n\n{text[:4000]}"},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            summary = response.choices[0].message.content
            logger.debug(f"요약 완료: {len(text)}자 → {len(summary)}자")
            return summary
        except Exception as e:
            logger.error(f"요약 중 오류 발생: {e}")
            return None

    def summarize_batch(self, texts: List[str], batch_size: int = 5) -> List[Optional[str]]:
        results = []
        for i, text in enumerate(texts):
            results.append(self.summarize(text))
            if (i + 1) % batch_size == 0:
                logger.info(f"배치 요약 진행: {i + 1}/{len(texts)}")
        logger.info(f"배치 요약 완료: 총 {len(texts)}건")
        return results

    def is_available(self) -> bool:
        return self.client is not None
