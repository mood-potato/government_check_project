import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

import httpx
import pdfplumber
from loguru import logger

from pipelines.base import BaseExtractor, BaseLoader, BasePipeline, BaseTransformer
from pipelines.utils.db import get_postgres_connection, update_get_pdf_status


NON_SPEECH_KEYWORDS = [
    "출석 의원",
    "개의 시",
    "산회 선포",
    "의석 배치",
    "교섭단체",
    "의안 심사",
    "보고서 제출",
    "요구서",
    "서면질문서",
    "청원",
    "청가",
    "의원 등록",
    "의원 사직",
    "의원 퇴직",
    "의석 승계",
    "상임위원",
    "소위원장",
    "특별위원",
    "통지",
    "집회",
    "본회의장 의석",
    "출석 위원",
    "출석 전문위원",
    "정부측 및 기타 참석자",
    "법원측 참석자",
    "출석 진술인",
]

APPENDIX_MARKERS = [
    "◯출석 의원",
    "◯출석 위원",
    "◯출석 전문위원",
    "◯정부측 및 기타 참석자",
    "◯법원측 참석자",
    "◯출석 진술인",
    "◯본회의장 의석",
    "◯개의 시",
    "◯산회 선포",
]

KNOWN_TITLES_PATTERN = re.compile(
    r"^(의장|부의장|의사국장|감사원장|국무총리|진술인|수석전문위원|전문위원"
    r"|[가-힣]+부\s*총리"
    r"|[가-힣]+부?\s*장관|[가-힣]*위원장(?:대리)?|위원|(?:[가-힣]+ )*의원"
    r"|[가-힣]+처장|[가-힣]+청장|국무위원)\s+"
)

SPEAKER_HEADER_PATTERN = re.compile(
    r"^◯(?P<speaker>"
    r"(?:[가-힣]{2,5}\s+(?:위원|의원|장관|차관|처장|청장|실장|교수|변호사))"
    r"|(?:(?:의장|부의장|의사국장|감사원장|국무총리|진술인|수석전문위원|전문위원"
    r"|[가-힣]+부\s*총리|[가-힣]+부?\s*장관|[가-힣]*위원장(?:대리)?|위원"
    r"|(?:[가-힣]+ )*의원|[가-힣]+처장|[가-힣]+청장|국무위원)\s+[가-힣]{2,5})"
    r")\s*(?P<speech>[\s\S]*?)(?=^◯|\Z)",
    re.MULTILINE,
)


def update_bill_url_get_pdf_status(connection, bill_url_id: str, status: bool) -> None:
    """bill_url의 PDF 처리 상태를 갱신합니다.

    Args:
        connection: PostgreSQL 연결 객체입니다.
        bill_url_id: `bill_url.id` 값입니다.
        status: PDF 처리 성공 여부입니다.
    """
    query = "UPDATE bill_url SET get_pdf = %s WHERE id = %s"
    with connection.cursor() as cur:
        cur.execute(query, (status, bill_url_id))
        connection.commit()


def _column_names(description) -> List[str]:
    """DB 커서 description에서 컬럼명을 가져옵니다."""
    names = []
    for column in description:
        if hasattr(column, "name"):
            names.append(column.name)
        else:
            names.append(column[0])
    return names


def _is_local_pdf_source(source: str) -> bool:
    """PDF 소스가 로컬 파일 경로인지 확인합니다."""
    parsed = urlparse(source)
    return parsed.scheme in ("", "file")


def _local_pdf_path(source: str) -> Path:
    """로컬 PDF 소스 문자열을 파일 경로로 변환합니다."""
    parsed = urlparse(source)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    return Path(source)


def _extract_text_from_pdf_source(source: str) -> str:
    """로컬 경로 또는 URL PDF에서 텍스트를 추출합니다."""
    if _is_local_pdf_source(source):
        with pdfplumber.open(_local_pdf_path(source)) as pdf:
            return "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )

    with httpx.Client(timeout=10.0) as client:
        response = client.get(source)
        response.raise_for_status()
        with pdfplumber.open(BytesIO(response.content)) as pdf:
            return "\n".join(
                page.extract_text() for page in pdf.pages if page.extract_text()
            )


class PDFToSpeechExtractor(BaseExtractor):
    """PDF URL 처리 및 텍스트 추출을 수행합니다.

    Args:
        pdf_url: 단일 PDF URL입니다.
        title: 단일 PDF 제목입니다.
        date: 단일 PDF 회의일입니다.
        connection: PDF URL 목록을 조회할 PostgreSQL 연결입니다.
    """

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
        """처리되지 않은 PDF URL 목록을 조회합니다.

        Returns:
            `get_pdf = false`인 PDF URL row 목록입니다.

        Raises:
            ValueError: DB 연결이 없는 경우입니다.
        """
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
        """PDF 한 건을 다운로드하고 텍스트를 추출합니다.

        Args:
            row: `pdf_url` 테이블에서 조회한 PDF URL row입니다.

        Returns:
            PDF 텍스트와 메타데이터 딕셔너리입니다.
        """
        pdf_url_id = row.get("pdf_url_id")
        pdf_url = row.get("pdf_url")
        title = row.get("title")
        date = row.get("date")
        confer_number = row.get("confer_number")
        dae_number = row.get("dae_number")
        class_name = row.get("class_name")

        try:
            text = _extract_text_from_pdf_source(pdf_url)
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
        """처리 대상 PDF 전체를 병렬로 추출합니다.

        Args:
            max_workers: PDF 다운로드와 파싱에 사용할 worker 수입니다.

        Returns:
            추출된 PDF 텍스트와 메타데이터 목록입니다.
        """
        rows = self.fetch_pdf_urls()
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.extract_one, row) for row in rows]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        return results

    def extract(self) -> List[dict]:
        """PDF URL 목록을 병렬로 처리하고 텍스트를 추출합니다."""
        return self.extract_all()


class BillURLToSpeechExtractor(BaseExtractor):
    """bill_url에 저장된 회의록 PDF에서 텍스트를 추출합니다.

    Args:
        connection: bill_url 목록을 조회할 PostgreSQL 연결입니다.
    """

    def __init__(self, connection=None):
        self.connection = connection

    def fetch_bill_urls(self) -> List[Dict[str, str]]:
        """처리되지 않은 bill_url 목록을 조회합니다.

        Returns:
            `bill_url.get_pdf = false`인 PDF row 목록입니다.

        Raises:
            ValueError: DB 연결이 없는 경우입니다.
        """
        if self.connection is None:
            raise ValueError("DB connection is not provided.")

        query = """
            SELECT
                bu.id AS bill_url_id,
                bu.download_url,
                bu.agenda_name,
                bu.meeting_type,
                bu.meeting_id,
                bu.dae_number,
                bu.meeting_date,
                COALESCE(bi.confer_number, 0) AS confer_number
            FROM bill_url bu
            LEFT JOIN bill_info bi
              ON bi.bill_id = bu.agenda_id
             AND bi.meeting_id = bu.meeting_id
            WHERE bu.get_pdf = false
            ORDER BY bu.meeting_date, bu.created_at
        """
        with self.connection.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            column_names = _column_names(cur.description)
        return [dict(zip(column_names, row)) for row in rows]

    def extract_one(self, row: Dict[str, str]) -> Dict[str, str]:
        """bill_url PDF 한 건에서 텍스트와 발언 메타데이터를 추출합니다.

        Args:
            row: `bill_url` 테이블에서 조회한 PDF row입니다.

        Returns:
            기존 PDFToSpeechTransformer 입력 형식의 딕셔너리입니다.
        """
        bill_url_id = row.get("bill_url_id")
        download_url = row.get("download_url")
        title = row.get("agenda_name")

        try:
            text = _extract_text_from_pdf_source(download_url)
            self.log_info(f"✅ bill_url PDF 처리 완료: {title}")
            return {
                "pdf_url_id": f"bill_url:{bill_url_id}",
                "bill_url_id": bill_url_id,
                "title": title,
                "date": row.get("meeting_date"),
                "text": text,
                "confer_number": row.get("confer_number") or 0,
                "dae_number": row.get("dae_number"),
                "class_name": row.get("meeting_type"),
                "file_path": download_url,
            }
        except Exception as e:
            self.log_info(f"❌ {title} bill_url PDF 처리 실패: {e}")
            if self.connection is not None:
                update_bill_url_get_pdf_status(self.connection, bill_url_id, False)
            raise

    def extract_all(self, max_workers: int = 10) -> List[Dict[str, str]]:
        """처리 대상 bill_url PDF 전체를 병렬로 추출합니다."""
        rows = self.fetch_bill_urls()
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.extract_one, row) for row in rows]
            for future in as_completed(futures):
                results.append(future.result())

        return results

    def extract(self) -> List[dict]:
        """bill_url 목록을 병렬로 처리하고 텍스트를 추출합니다."""
        return self.extract_all()


class PDFToSpeechTransformer(BaseTransformer):
    """국회 회의록 PDF 텍스트를 발언 단위 데이터로 변환합니다."""

    def __init__(self, enable_summary: bool = False):
        self.speaker_pattern = SPEAKER_HEADER_PATTERN
        self.enable_summary = enable_summary
        self.summarizer: Optional["SpeechSummarizer"] = None

        if enable_summary:
            try:
                from pipelines.utils.speech import SpeechSummarizer

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
        """전체 텍스트를 전처리합니다."""
        text = re.sub(
            r"^제\d+회-.+\(\d{4}년\d{1,2}월\d{1,2}일\)\s+\d+\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"^\d+\s+제\d+회-.+\(\d{4}년\d{1,2}월\d{1,2}일\)\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )

        earliest_pos = len(text)
        for marker in APPENDIX_MARKERS:
            pos = text.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos
        if earliest_pos < len(text):
            text = text[:earliest_pos]

        return text

    def _is_page_header_line(self, line: str) -> bool:
        """페이지 머리말/꼬리말 줄인지 검사합니다."""
        line = line.strip()
        if re.fullmatch(
            r"제\d+회-.+\(\d{4}년\d{1,2}월\d{1,2}일\)\s+\d+",
            line,
        ):
            return True
        if re.fullmatch(
            r"\d+\s+제\d+회-.+\(\d{4}년\d{1,2}월\d{1,2}일\)",
            line,
        ):
            return True
        return False

    def _is_separator_line(self, line: str) -> bool:
        """발언 구분용 점선인지 검사합니다."""
        compact_line = re.sub(r"\s+", "", line)
        return bool(compact_line) and set(compact_line) <= {"…", ".", "ㆍ"}

    def _is_agenda_item_line(self, line: str) -> bool:
        """의사일정 법안 목록 줄인지 검사합니다."""
        line = line.strip()
        if not re.match(r"^\d+\.\s+", line):
            return False
        return bool(
            re.search(
                r"법률안|특별법안|기본법|지원법|진흥법|관리법|운영법|설치법|개정법률안",
                line,
            )
        )

    def _remove_agenda_list_lines(self, text: str) -> str:
        """발언 중간에 삽입된 의사일정 법안 목록을 제거합니다."""
        cleaned_lines = []
        skipping_agenda = False

        for line in text.splitlines():
            stripped_line = line.strip()
            if self._is_agenda_item_line(stripped_line):
                skipping_agenda = True
                continue

            if skipping_agenda:
                if re.match(r"^◯", stripped_line):
                    skipping_agenda = False
                    cleaned_lines.append(line)
                    continue
                if re.match(r"^\d{1,2}시\d{1,2}분", stripped_line):
                    skipping_agenda = False
                    cleaned_lines.append(line)
                    continue
                if not stripped_line:
                    skipping_agenda = False
                    cleaned_lines.append(line)
                    continue
                if re.match(r"^[가-힣]", stripped_line) and not re.search(
                    r"법률안|의안번호|위원장 제출|대표발의|정부 제출",
                    stripped_line,
                ):
                    skipping_agenda = False
                    cleaned_lines.append(line)
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _clean_speech_text(self, text: str) -> str:
        """발언 텍스트에서 노이즈를 제거합니다."""
        text = self._remove_agenda_list_lines(text)
        cleaned_lines = []
        for line in text.splitlines():
            if self._is_page_header_line(line) or self._is_separator_line(line):
                continue
            cleaned_lines.append(line)
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\(\d{1,2}시\d{1,2}분[^)]*\)", "", text)
        text = re.sub(r"\(일동 [가-힣]+\)", "", text)
        text = re.sub(r"\(전자[가-힣]*투표\)", "", text)
        text = re.sub(r"\([가-힣]+은? 부록으로 보존함\)", "", text)
        text = re.sub(r"^o\s+.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_non_speech(self, speaker_raw: str) -> bool:
        """비발언 항목인지 검사합니다."""
        for keyword in NON_SPEECH_KEYWORDS:
            if keyword in speaker_raw:
                return True
        if re.search(r"법률?안|법률 일부개정|기본법 일부개정", speaker_raw):
            return True
        return False

    def _parse_speaker(self, raw: str) -> Tuple[Optional[str], str]:
        """발언자 문자열에서 직책과 이름을 분리합니다.

        Args:
            raw: PDF에서 추출한 발언자 원문입니다.

        Returns:
            직책과 이름 튜플입니다. 직책이 없으면 첫 번째 값은 None입니다.
        """
        raw = raw.strip()
        m = KNOWN_TITLES_PATTERN.match(raw)
        if m:
            title = m.group(1).strip()
            name = raw[m.end() :].strip()
            if name:
                return (title, name)

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
        """전체 회의록 텍스트에서 발언 정보를 파싱합니다.

        Args:
            pdf_url_id: PDF URL ID입니다.
            text: 전체 회의록 텍스트입니다.
            title: 회의록 제목입니다.
            date: 회의일입니다.
            confer_number: 회의번호입니다.
            dae_number: 국회 대수입니다.
            class_name: 위원회 종류입니다.
            file_path: PDF URL입니다.

        Returns:
            발언 데이터가 담긴 딕셔너리 목록입니다.
        """
        text = self._preprocess_text(text)

        speech_list = []

        for idx, match in enumerate(self.speaker_pattern.finditer(text), start=1):
            speaker_raw = match.group("speaker").strip()
            speech = match.group("speech").strip()

            if self._is_non_speech(speaker_raw):
                continue

            speech = self._clean_speech_text(speech)
            speaker_title, speaker_name = self._parse_speaker(speaker_raw)

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

        for i, speech in enumerate(speech_list, start=1):
            speech["speech_number"] = i

        return speech_list


class PDFToSpeechLoader(BaseLoader):
    """발언 데이터를 PostgreSQL에 저장합니다."""

    def __init__(self, connection):
        super().__init__(connection)

    def _create_tables(self) -> None:
        """필요한 데이터베이스 테이블과 인덱스를 생성합니다."""
        try:
            queries = [
                """
                CREATE TABLE IF NOT EXISTS speeches (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    pdf_url_id TEXT NOT NULL,
                    speaker_id UUID REFERENCES speakers(id) ON DELETE SET NULL,
                    speaker_name TEXT NOT NULL,
                    speaker_title TEXT,
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
            ]
            for query in queries:
                self._execute_query(query)

            migration_queries = [
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS title TEXT;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS summary TEXT;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS vectorized BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS speaker_name TEXT;",
                "ALTER TABLE speeches ADD COLUMN IF NOT EXISTS speaker_title TEXT;",
                """
                UPDATE speeches s
                SET speaker_name = sp.name
                FROM speakers sp
                WHERE s.speaker_id = sp.id
                  AND s.speaker_name IS NULL;
                """,
                "ALTER TABLE speeches ALTER COLUMN speaker_id DROP NOT NULL;",
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'unique_speech'
                    ) THEN
                        ALTER TABLE speeches
                        ADD CONSTRAINT unique_speech UNIQUE (pdf_url_id, speech_number);
                    END IF;
                END $$;
                """,
            ]
            for query in migration_queries:
                self._execute_query(query)

            index_queries = [
                """CREATE INDEX IF NOT EXISTS idx_speeches_pdf_url_id ON speeches(pdf_url_id);""",
                """CREATE INDEX IF NOT EXISTS idx_speeches_speaker_id ON speeches(speaker_id);""",
                """CREATE INDEX IF NOT EXISTS idx_speeches_speaker_name ON speeches(speaker_name);""",
                """CREATE INDEX IF NOT EXISTS idx_speeches_vectorized ON speeches(vectorized);""",
            ]
            for query in index_queries:
                self._execute_query(query)

            logger.info("✅ 데이터베이스 테이블 생성 완료")
        except Exception as e:
            logger.error(f"❌ 데이터베이스 테이블 생성 실패: {e}")
            raise

    def create_table(self) -> None:
        """필요한 데이터베이스 테이블을 생성합니다."""
        self._create_tables()

    def _find_speaker_id(self, speaker_name: str, dae_number: int) -> Optional[str]:
        """국회의원 마스터에서 발언자 ID를 조회합니다."""
        query = """
            SELECT id
            FROM speakers
            WHERE name = %s
              AND assembly_number = %s
        """
        results = self._execute_query(query, (speaker_name, dae_number))
        if not results:
            logger.warning(
                f"⚠️ 국회의원 마스터에 없는 발언자 - {speaker_name} ({dae_number}대)"
            )
            return None
        if len(results) > 1:
            logger.warning(
                f"⚠️ 발언자 매칭이 여러 명입니다 - {speaker_name} ({dae_number}대)"
            )
            return None
        return str(results[0][0])

    def _save_all_data(self, speech_data: List[Dict]) -> None:
        """발언 데이터 목록을 저장합니다."""
        speaker_map = {}
        for speech in speech_data:
            key = (speech["speaker"], speech["dae_number"])
            if key not in speaker_map:
                speaker_map[key] = self._find_speaker_id(*key)

        speech_query = """
            INSERT INTO speeches (
                pdf_url_id,
                speech_number,
                speaker_id,
                speaker_name,
                speaker_title,
                date,
                title,
                class_name,
                confer_number,
                dae_number,
                speech,
                summary,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (pdf_url_id, speech_number) DO NOTHING
        """
        for idx, speech in enumerate(speech_data):
            speaker_id = speaker_map.get((speech["speaker"], speech["dae_number"]))
            self._execute_query(
                speech_query,
                (
                    speech["pdf_url_id"],
                    idx + 1,
                    speaker_id,
                    speech["speaker"],
                    speech.get("speaker_title"),
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
        """파싱된 발언 데이터를 PostgreSQL에 저장합니다."""
        if not speech_data:
            logger.warning("⚠️ 저장할 발언 데이터가 없습니다.")
            return

        first_speech = speech_data[0]
        required_fields = ("speaker", "text", "timestamp")

        if not all(k in first_speech for k in required_fields):
            logger.error(f"❌ 필수 항목이 누락되었습니다: {required_fields}")
            return

        try:
            self._execute_query("BEGIN")
            self._save_all_data(speech_data)
            self._execute_query("COMMIT")
            logger.info(f"✅ PostgreSQL 저장 완료 - {first_speech['pdf_url_id']}")
        except Exception as e:
            self._execute_query("ROLLBACK")
            logger.error(f"❌ PostgreSQL 저장 실패: {e}")
            raise


class PDFToSpeechPipeline(BasePipeline):
    """PDF 회의록에서 발언 데이터를 추출해 저장하는 파이프라인입니다."""

    def __init__(self):
        connection = get_postgres_connection()
        self.connection = connection
        extractor = PDFToSpeechExtractor(connection=connection)
        loader = PDFToSpeechLoader(connection=connection)
        transformer = PDFToSpeechTransformer()
        super().__init__(extractor, loader, transformer)

    def run(self):
        """PDF 추출, 발언 변환, DB 저장을 순서대로 실행합니다."""
        logger.info("✅ PDF 단위 추출 시작")
        rows = self.extractor.fetch_pdf_urls()
        logger.info(f"✅ 처리 대상 PDF: 총 {len(rows)}건")

        for row in rows:
            try:
                item = self.extractor.extract_one(row)
            except Exception as e:
                logger.error(f"❌ PDF 추출 중 오류 발생: {e}")
                continue

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


class BillURLToSpeechPipeline(BasePipeline):
    """bill_url 회의록 PDF에서 발언 데이터를 추출해 저장하는 파이프라인입니다."""

    def __init__(self):
        connection = get_postgres_connection()
        self.connection = connection
        extractor = BillURLToSpeechExtractor(connection=connection)
        loader = PDFToSpeechLoader(connection=connection)
        transformer = PDFToSpeechTransformer()
        super().__init__(extractor, loader, transformer)
        self.connection = connection

    def run(self):
        """bill_url PDF 추출, 발언 변환, DB 저장을 순서대로 실행합니다."""
        logger.info("✅ bill_url PDF 단위 추출 시작")
        rows = self.extractor.fetch_bill_urls()
        logger.info(f"✅ bill_url 처리 대상: 총 {len(rows)}건")

        self.loader.create_table()

        for row in rows:
            try:
                item = self.extractor.extract_one(row)
            except Exception as e:
                logger.error(f"❌ bill_url PDF 추출 중 오류 발생: {e}")
                continue

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
                logger.info(f"✅ bill_url DB 저장 완료: {len(transformed_result)}건")
                update_bill_url_get_pdf_status(
                    self.connection, item["bill_url_id"], True
                )
            except Exception as e:
                update_bill_url_get_pdf_status(
                    self.connection, item["bill_url_id"], False
                )
                logger.error(f"❌ bill_url DB 저장 중 오류 발생: {e}")
