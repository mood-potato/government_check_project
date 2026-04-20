import datetime
import re
from typing import Dict, List, Optional, Tuple

from loguru import logger

from pipelines.base.base_transformer import BaseTransformer

# 비발언 항목 키워드 (부록/메타데이터)
NON_SPEECH_KEYWORDS = [
    "출석 의원", "개의 시", "산회 선포", "의석 배치",
    "교섭단체", "의안 심사", "보고서 제출", "요구서",
    "서면질문서", "청원", "청가", "의원 등록", "의원 사직",
    "의원 퇴직", "의석 승계", "상임위원", "소위원장",
    "특별위원", "통지", "집회", "본회의장 의석",
]

# 부록 섹션 시작 마커
APPENDIX_MARKERS = [
    "◯출석 의원",
    "◯본회의장 의석",
    "◯개의 시",
    "◯산회 선포",
]

# 알려진 직책 패턴
KNOWN_TITLES_PATTERN = re.compile(
    r"^(의장|부의장|의사국장|감사원장|국무총리|[가-힣]+부\s*총리"
    r"|[가-힣]+부?\s*장관|[가-힣]*위원장(?:대리)?|위원|(?:[가-힣]+ )*의원"
    r"|[가-힣]+처장|[가-힣]+청장|국무위원)\s+"
)


class PDFToSpeechTransformer(BaseTransformer):
    """
    국회 회의록 PDF에서 발언 텍스트를 파싱하여 구조화된 리스트로 반환하는 클래스
    """

    def __init__(self, enable_summary: bool = False):
        self.speaker_pattern = re.compile(
            r"◯([\w]+ [\w]+)\s*\n*([\s\S]+?)(?=\n◯|\Z)", re.MULTILINE
        )
        self.enable_summary = enable_summary
        self.summarizer: Optional["SpeechSummarizer"] = None

        if enable_summary:
            try:
                from pipelines.utils.summarizer import SpeechSummarizer
                self.summarizer = SpeechSummarizer()
                if self.summarizer.is_available():
                    logger.info("요약 기능이 활성화되었습니다.")
                else:
                    logger.warning("OPENAI_API_KEY가 없어 요약 기능이 비활성화됩니다.")
                    self.summarizer = None
            except ImportError as e:
                logger.warning(f"요약 모듈 로드 실패: {e}")
                self.summarizer = None

    def _preprocess_text(self, text: str) -> str:
        """전체 텍스트 전처리: 페이지 헤더 제거, 부록 섹션 잘라내기"""
        # 페이지 헤더 제거: "제431회-제1차(2026년1월15일) 3"
        text = re.sub(r"제\d+회-제\d+차\([^)]*\)\s*\d+", "", text)

        # 부록 섹션 감지 및 잘라내기 — 텍스트에서 가장 먼저 나타나는 마커 기준
        earliest_pos = len(text)
        for marker in APPENDIX_MARKERS:
            pos = text.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
        if earliest_pos < len(text):
            text = text[:earliest_pos]

        return text

    def _clean_speech_text(self, text: str) -> str:
        """발언 텍스트에서 노이즈 제거"""
        # 타임스탬프 제거: (14시41분), (10시05분 개의)
        text = re.sub(r"\(\d{1,2}시\d{1,2}분[^)]*\)", "", text)
        # 무대지시 제거: (일동 기립), (일동 박수)
        text = re.sub(r"\(일동 [가-힣]+\)", "", text)
        # 전자투표 제거: (전자투표), (전자기립투표)
        text = re.sub(r"\(전자[가-힣]*투표\)", "", text)
        # 절차 메모 제거: (대안은 부록으로 보존함)
        text = re.sub(r"\([가-힣]+은? 부록으로 보존함\)", "", text)
        # 의사일정 마커 제거: "o 의원(이소희) 선서 및 인사" (줄 단위)
        text = re.sub(r"^o\s+.*$", "", text, flags=re.MULTILINE)
        # 연속 공백 정리
        text = re.sub(r"[ \t]+", " ", text)
        # 연속 줄바꿈 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_non_speech(self, speaker_raw: str) -> bool:
        """비발언 항목인지 검사. speaker_raw는 2단어 fragment 또는 full_context 모두 가능."""
        for keyword in NON_SPEECH_KEYWORDS:
            if keyword in speaker_raw:
                return True
        # 법률안/의안명 패턴: "~법 일부개정법률안", "~법률안", "~법률 일부개정법률안"
        if re.search(r"법률?안|법률 일부개정|기본법 일부개정", speaker_raw):
            return True
        return False

    def _parse_speaker(self, raw: str) -> Tuple[Optional[str], str]:
        """
        발언자 문자열에서 직책과 이름을 분리.
        '의장 우원식' → ('의장', '우원식')
        '이소희 의원' → ('의원', '이소희')
        '위원 김철수' → ('위원', '김철수')
        직책 없으면 (None, raw)
        """
        raw = raw.strip()
        # 패턴1: 직책이 앞에 오는 경우 "의장 우원식"
        m = KNOWN_TITLES_PATTERN.match(raw)
        if m:
            title = m.group(1).strip()
            name = raw[m.end():].strip()
            if name:
                return (title, name)

        # 패턴2: 이름 뒤에 직책이 오는 경우 "이소희 의원" (2~4글자 이름 + 직책)
        m2 = re.match(r"^([가-힣]{2,4})\s+(의원|위원장|위원|의장|부의장)$", raw)
        if m2:
            return (m2.group(2), m2.group(1))

        return (None, raw)

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
        # 전처리
        text = self._preprocess_text(text)

        speech_list = []

        for idx, match in enumerate(self.speaker_pattern.finditer(text), start=1):
            speaker_raw = match.group(1).strip()
            speech = match.group(2).strip()

            # full_context = speaker_raw + speech 앞 80자 → 법률안 전체 이름이 보임
            full_context = speaker_raw + " " + speech[:80]
            if self._is_non_speech(full_context):
                continue

            # 발언 텍스트 정제
            speech = self._clean_speech_text(speech)

            # 직책/이름 분리
            speaker_title, speaker_name = self._parse_speaker(speaker_raw)

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
                    "speaker": speaker_name,
                    "speaker_title": speaker_title,
                    "speech_number": idx,
                    "text": speech,
                    "summary": summary,
                    "timestamp": datetime.datetime.now(),
                    "file_path": file_path,
                }
            )

        # speech_number 재정렬 (필터링 후)
        for i, s in enumerate(speech_list, start=1):
            s["speech_number"] = i

        return speech_list
