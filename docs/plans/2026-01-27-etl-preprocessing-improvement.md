# ETL 전처리 개선 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 제22대국회 제431회 PDF 분석 결과를 바탕으로 PDFToSpeechTransformer의 발언 추출 정확도를 개선한다.

**Architecture:** 현재 regex `◯([\w]+ [\w]+)` 는 52개 매치 중 19개가 오탐(비발언 항목)이다. 텍스트 전처리(페이지 헤더/부록 제거) → regex 개선(블랙리스트 필터링) → 발언 텍스트 정제(노이즈 제거) → 직책/이름 분리 순서로 개선한다.

**Tech Stack:** Python 3.12, pdfplumber, re, pytest, PostgreSQL (psycopg2)

---

## 발견된 문제점 요약

| 문제 | 현재 | 목표 |
|------|------|------|
| False Positives | 99 matches → 19 오탐 | ~80 matches → 0 오탐 |
| 발언 텍스트 노이즈 | 페이지 헤더, 타임스탬프, 무대지시 포함 | 순수 발언 텍스트만 |
| 발언자명 | "의장 우원식" (직책+이름 혼합) | title="의장", name="우원식" 분리 |
| 부록 파싱 | 투표결과 등이 발언으로 오탐 | 부록 섹션 자동 제거 |

**오탐 키워드 예시:** "개의 시", "출석 의원", "본회의장 의석", "교섭단체 가입", "의안 심사", "군인사법 일부개정법률안", "농어촌특별세법 일부개정법률안"

---

## Task 1: 텍스트 전처리 - 페이지 헤더 제거

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py`
- Test: `test/unit/test_transformers.py`

**Step 1: Write the failing test**

Add to `test/unit/test_transformers.py`:

```python
class TestPreprocessText:
    def test_removes_page_headers(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "제431회-제1차(2026년1월15일) 3\n◯의장 우원식 오늘 회의를 시작합니다."
        result = t._preprocess_text(text)
        assert "제431회-제1차(2026년1월15일) 3" not in result
        assert "◯의장 우원식 오늘 회의를 시작합니다." in result

    def test_removes_multiple_page_headers(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "제431회-제1차(2026년1월15일) 3\n본문1\n4 제431회-제1차(2026년1월15일)\n본문2"
        result = t._preprocess_text(text)
        assert "본문1" in result
        assert "본문2" in result
        assert "제431회" not in result
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_transformers.py::TestPreprocessText -v`
Expected: FAIL with "has no attribute '_preprocess_text'"

**Step 3: Write minimal implementation**

Add to `modules/transform/pdf_to_speech_transformer.py`:

```python
def _preprocess_text(self, text: str) -> str:
    """Remove page headers and normalize text"""
    # 페이지 헤더 패턴: "제431회-제1차(2026년1월15일) 3" 또는 "4 제431회-제1차(2026년1월15일)"
    text = re.sub(r"^\d*\s*제\d+회-제\d+차\([^)]+\)\s*\d*\s*$", "", text, flags=re.MULTILINE)
    return text
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_transformers.py::TestPreprocessText -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "✨ Add: 페이지 헤더 제거 전처리 함수"
```

---

## Task 2: 텍스트 전처리 - 부록 섹션 제거

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py`
- Test: `test/unit/test_transformers.py`

**Step 1: Write the failing test**

```python
class TestPreprocessRemovesAppendix:
    def test_removes_appendix_from_attendance_marker(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯의장 우원식 회의를 시작합니다.\n◯출석 의원\n김가 김나 김다\n◯본회의장 의석\n좌석표"
        result = t._preprocess_text(text)
        assert "◯의장 우원식 회의를 시작합니다." in result
        assert "◯출석 의원" not in result
        assert "◯본회의장 의석" not in result

    def test_keeps_speech_before_appendix(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯의장 우원식 첫 발언\n◯이소희 의원 두번째 발언\n◯개의 시\n(14시30분)\n◯출석 의원\n명단"
        result = t._preprocess_text(text)
        assert "◯이소희 의원 두번째 발언" in result
        assert "◯개의 시" not in result
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_transformers.py::TestPreprocessRemovesAppendix -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Update `_preprocess_text` in `modules/transform/pdf_to_speech_transformer.py`:

```python
# 부록 시작 키워드 목록 (클래스 변수로)
APPENDIX_MARKERS = [
    "◯출석 의원", "◯출석 국무위원", "◯출석 정부위원",
    "◯본회의장 의석", "◯개의 시", "◯산회 시",
    "◯교섭단체 가입", "◯교섭단체 대표의원", "◯교섭단체 소속의원",
    "◯의원 등록", "◯의원 사직", "◯의원 퇴직", "◯의석 승계",
    "◯상임위원 개선", "◯소위원장 선임", "◯특별위원 선임",
    "◯의안 심사", "◯의안 제출", "◯요구서 제출",
    "◯보고서 제출", "◯서면질문서 제출", "◯청원 제출",
    "◯청가 의원", "◯출장 의원", "◯기타 참석자",
    "◯국회 참석자", "◯통지", "◯집회",
]

def _preprocess_text(self, text: str) -> str:
    """Remove page headers and appendix sections"""
    # 1. 페이지 헤더 제거
    text = re.sub(r"^\d*\s*제\d+회-제\d+차\([^)]+\)\s*\d*\s*$", "", text, flags=re.MULTILINE)

    # 2. 부록 섹션 제거: 첫 부록 마커 이후 모든 텍스트 제거
    earliest_pos = len(text)
    for marker in self.APPENDIX_MARKERS:
        pos = text.find(marker)
        if pos != -1 and pos < earliest_pos:
            earliest_pos = pos

    if earliest_pos < len(text):
        text = text[:earliest_pos]

    return text
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_transformers.py::TestPreprocessRemovesAppendix -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "✨ Add: 부록 섹션 자동 제거"
```

---

## Task 3: 발언 텍스트 노이즈 제거

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py`
- Test: `test/unit/test_transformers.py`

**Step 1: Write the failing test**

```python
class TestCleanSpeechText:
    def test_removes_timestamps(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "회의를 시작합니다.\n(14시41분)\n다음 안건입니다."
        result = t._clean_speech_text(text)
        assert "(14시41분)" not in result
        assert "회의를 시작합니다." in result

    def test_removes_stage_directions(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "선서하겠습니다.\n(일동 기립)\n선서문을 읽겠습니다.\n(일동 착석)"
        result = t._clean_speech_text(text)
        assert "(일동 기립)" not in result
        assert "(일동 착석)" not in result
        assert "선서하겠습니다." in result

    def test_removes_electronic_vote(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "투표해 주시기 바랍니다.\n(전자투표)\n투표를 마치겠습니다."
        result = t._clean_speech_text(text)
        assert "(전자투표)" not in result

    def test_removes_procedural_notes(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "감사합니다.\n(대안은 부록으로 보존함)\n(찬반 의원 성명은 끝에 실음)"
        result = t._clean_speech_text(text)
        assert "(대안은 부록으로 보존함)" not in result
        assert "(찬반 의원 성명은 끝에 실음)" not in result

    def test_removes_agenda_markers(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "수고하셨습니다.\no 의원(이소희) 선서 및 인사\n다음 안건입니다."
        result = t._clean_speech_text(text)
        assert "o 의원(이소희) 선서 및 인사" not in result
        assert "수고하셨습니다." in result

    def test_strips_extra_whitespace(self):
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "첫번째 줄\n\n\n\n두번째 줄"
        result = t._clean_speech_text(text)
        assert "\n\n\n" not in result
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_transformers.py::TestCleanSpeechText -v`
Expected: FAIL with "has no attribute '_clean_speech_text'"

**Step 3: Write minimal implementation**

Add to `modules/transform/pdf_to_speech_transformer.py`:

```python
def _clean_speech_text(self, text: str) -> str:
    """Remove noise from speech text"""
    # 타임스탬프: (14시41분), (14시49분 투표개시), (15시09분 투표종료)
    text = re.sub(r"\(\d{1,2}시\d{1,2}분[^)]*\)", "", text)

    # 무대지시: (일동 기립), (일동 착석), (박수)
    text = re.sub(r"\(일동 [가-힣]+\)", "", text)

    # 전자투표: (전자투표), (전자 무기명투표)
    text = re.sub(r"\(전자[가-힣 ]*투표\)", "", text)

    # 절차 메모: (대안은 부록으로 보존함), (찬반 의원 성명은 끝에 실음), (심사보고서는 부록으로 보존함)
    text = re.sub(r"\([가-힣 ]+(?:부록으로 보존함|끝에 실음)\)", "", text)

    # 의장 동작: (우원식 의장, 발언대로 내려와 선서문을 받음) 등
    text = re.sub(r"\([가-힣]+ [가-힣]+,\s*[^)]+\)", "", text)

    # 의사일정 마커: "o 의원(이소희) 선서 및 인사", "o 감사원장(김호철) 인사"
    text = re.sub(r"^o\s+.+$", "", text, flags=re.MULTILINE)

    # 의사일정 번호: "1. 국회운영위원장 보궐선거" (줄 시작이 숫자+점)
    text = re.sub(r"^\d+\.\s+.+$", "", text, flags=re.MULTILINE)

    # 투표 결과 문구: "(투표 결과는 끝에 실음)"
    text = re.sub(r"\(투표 결과는[^)]+\)", "", text)

    # 연속 빈줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_transformers.py::TestCleanSpeechText -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "✨ Add: 발언 텍스트 노이즈 제거 함수"
```

---

## Task 4: 발언자 regex 개선 (블랙리스트 필터링)

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py`
- Test: `test/unit/test_transformers.py`

**Step 1: Write the failing test**

```python
class TestImprovedSpeakerRegex:
    def test_matches_speaker_with_title_first(self):
        """◯의장 우원식 발언내용"""
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯의장 우원식 회의를 시작합니다."
        result = t.transform(
            pdf_url_id="test", text=text, title="test", date="2026-01-15",
            confer_number="1", dae_number="22", class_name="본회의", file_path="test"
        )
        assert len(result) == 1
        assert result[0]["speaker"] == "우원식"

    def test_matches_speaker_with_name_first(self):
        """◯이소희 의원 발언내용"""
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯이소희 의원 존경하는 국민 여러분!"
        result = t.transform(
            pdf_url_id="test", text=text, title="test", date="2026-01-15",
            confer_number="1", dae_number="22", class_name="본회의", file_path="test"
        )
        assert len(result) == 1
        assert result[0]["speaker"] == "이소희"

    def test_matches_long_title_speaker(self):
        """◯기후에너지환경노동위원장대리 박정 발언내용"""
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯기후에너지환경노동위원장대리 박정 법률안에 대하여 설명드리겠습니다."
        result = t.transform(
            pdf_url_id="test", text=text, title="test", date="2026-01-15",
            confer_number="1", dae_number="22", class_name="본회의", file_path="test"
        )
        assert len(result) == 1
        assert result[0]["speaker"] == "박정"

    def test_ignores_non_speech_bill_name(self):
        """◯군인사법 일부개정법률안 은 무시"""
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯군인사법 일부개정법률안(대안)\n내용\n◯의장 우원식 다음 안건입니다."
        result = t.transform(
            pdf_url_id="test", text=text, title="test", date="2026-01-15",
            confer_number="1", dae_number="22", class_name="본회의", file_path="test"
        )
        speakers = [r["speaker"] for r in result]
        assert "우원식" in speakers
        assert "군인사법" not in " ".join(speakers)

    def test_returns_speaker_title(self):
        """transform 결과에 speaker_title 필드 포함"""
        from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
        t = PDFToSpeechTransformer()
        text = "◯의장 우원식 회의를 시작합니다."
        result = t.transform(
            pdf_url_id="test", text=text, title="test", date="2026-01-15",
            confer_number="1", dae_number="22", class_name="본회의", file_path="test"
        )
        assert result[0]["speaker_title"] == "의장"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_transformers.py::TestImprovedSpeakerRegex -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Replace the speaker pattern and transform method in `modules/transform/pdf_to_speech_transformer.py`:

```python
import re
import datetime
from typing import List, Dict
from modules.base.base_transformer import BaseTransformer

class PDFToSpeechTransformer(BaseTransformer):

    # 부록/메타데이터 시작 마커 (부록 섹션 이후 텍스트 제거용)
    APPENDIX_MARKERS = [
        "◯출석 의원", "◯출석 국무위원", "◯출석 정부위원",
        "◯본회의장 의석", "◯개의 시", "◯산회 시",
        "◯교섭단체 가입", "◯교섭단체 대표의원", "◯교섭단체 소속의원",
        "◯의원 등록", "◯의원 사직", "◯의원 퇴직", "◯의석 승계",
        "◯상임위원 개선", "◯소위원장 선임", "◯특별위원 선임",
        "◯의안 심사", "◯의안 제출", "◯요구서 제출",
        "◯보고서 제출", "◯서면질문서 제출", "◯청원 제출",
        "◯청가 의원", "◯출장 의원", "◯기타 참석자",
        "◯국회 참석자", "◯통지", "◯집회",
    ]

    # 비발언 ◯ 항목 필터링용 키워드 (이 키워드로 시작하면 발언이 아님)
    NON_SPEECH_PREFIXES = [
        "출석", "개의", "산회", "의석", "교섭단체", "의안",
        "보고서", "요구서", "서면질문서", "청원", "청가",
        "의원 등록", "의원 사직", "의원 퇴직", "의석 승계",
        "상임위원", "소위원장", "특별위원", "통지", "집회",
        "국회 참석자", "기타 참석자", "출장", "노후계획도시",
        # 법률안 이름 패턴
        "군인사법", "농어촌특별세법", "미세먼지", "재난",
        "아동복지법", "자본시장", "전기통신", "주택법",
        "주식", "항공", "윤석열",
    ]

    def __init__(self, enable_summary: bool = False):
        self.summarizer = None
        if enable_summary:
            from modules.llm.summarizer import SpeechSummarizer
            self.summarizer = SpeechSummarizer()

        # 발언자 패턴: ◯ + (2글자 이상) + 공백 + (발언 시작)
        # 기존 regex를 유지하되, 후처리로 필터링
        self.speaker_pattern = re.compile(
            r"◯([\w]+ [\w]+)\s*\n*([\s\S]+?)(?=\n◯|\Z)",
            re.MULTILINE,
        )

    def _preprocess_text(self, text: str) -> str:
        """Remove page headers and appendix sections"""
        # 1. 페이지 헤더 제거
        text = re.sub(
            r"^\d*\s*제\d+회-제\d+차\([^)]+\)\s*\d*\s*$", "", text, flags=re.MULTILINE
        )

        # 2. 부록 섹션 제거
        earliest_pos = len(text)
        for marker in self.APPENDIX_MARKERS:
            pos = text.find(marker)
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos

        if earliest_pos < len(text):
            text = text[:earliest_pos]

        return text

    def _clean_speech_text(self, text: str) -> str:
        """Remove noise from speech text"""
        text = re.sub(r"\(\d{1,2}시\d{1,2}분[^)]*\)", "", text)
        text = re.sub(r"\(일동 [가-힣]+\)", "", text)
        text = re.sub(r"\(전자[가-힣 ]*투표\)", "", text)
        text = re.sub(r"\([가-힣 ]+(?:부록으로 보존함|끝에 실음)\)", "", text)
        text = re.sub(r"\([가-힣]+ [가-힣]+,\s*[^)]+\)", "", text)
        text = re.sub(r"^o\s+.+$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\d+\.\s+.+$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\(투표 결과는[^)]+\)", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _is_speech_match(self, raw_speaker: str) -> bool:
        """Check if matched ◯ entry is a real speech (not metadata)"""
        for prefix in self.NON_SPEECH_PREFIXES:
            if raw_speaker.startswith(prefix):
                return False
        return True

    def _parse_speaker(self, raw: str) -> tuple[str, str]:
        """Parse 'title name' or 'name title' into (title, name)

        Examples:
            '의장 우원식' → ('의장', '우원식')
            '이소희 의원' → ('의원', '이소희')
            '정무위원장대리 김상훈' → ('정무위원장대리', '김상훈')
            '감사원장 김호철' → ('감사원장', '김호철')
        """
        parts = raw.split()
        if len(parts) != 2:
            return ("", raw)

        # "이름 의원" 패턴: 뒷부분이 '의원'이면 이름이 앞
        if parts[1] == "의원":
            return ("의원", parts[0])

        # 그 외: 직책이 앞, 이름이 뒤
        return (parts[0], parts[1])

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
        """Parse all speeches from PDF text"""
        # 전처리
        text = self._preprocess_text(text)

        speech_list = []
        for idx, match in enumerate(self.speaker_pattern.finditer(text), start=1):
            raw_speaker = match.group(1).strip()
            speech_text = match.group(2).strip()

            # 비발언 항목 필터링
            if not self._is_speech_match(raw_speaker):
                continue

            # 직책/이름 분리
            speaker_title, speaker_name = self._parse_speaker(raw_speaker)

            # 발언 텍스트 정제
            speech_text = self._clean_speech_text(speech_text)
            if not speech_text:
                continue

            summary = None
            if self.summarizer:
                summary = self.summarizer.summarize(speech_text)

            speech_list.append({
                "pdf_url_id": pdf_url_id,
                "title": title,
                "date": date,
                "confer_number": confer_number,
                "dae_number": dae_number,
                "class_name": class_name,
                "speaker": speaker_name,
                "speaker_title": speaker_title,
                "speech_number": len(speech_list) + 1,
                "text": speech_text,
                "summary": summary,
                "timestamp": datetime.datetime.now(),
                "file_path": file_path,
            })

        return speech_list
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_transformers.py::TestImprovedSpeakerRegex -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "🔧 Fix: 발언자 regex 개선 및 오탐 필터링"
```

---

## Task 5: 기존 테스트 수정 및 conftest 업데이트

**Files:**
- Modify: `test/conftest.py`
- Modify: `test/unit/test_transformers.py`

**Step 1: conftest.py의 sample text 업데이트**

현재 conftest.py의 sample_pdf_text fixture를 확인하고, 새로운 `speaker` 필드 (이름만) 에 맞게 기존 테스트 수정.

기존 테스트 `TestPDFToSpeechTransformer`에서:
- `speaker` 값이 "의장 홍길동" → "홍길동"으로 변경
- `speaker_title` 필드 추가 검증

**Step 2: Run all tests**

Run: `uv run pytest test/unit/test_transformers.py -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add test/conftest.py test/unit/test_transformers.py
git commit -m "🔧 Fix: 기존 테스트를 개선된 transformer에 맞게 수정"
```

---

## Task 6: speakers 테이블 title 컬럼 추가

**Files:**
- Modify: `modules/load/pdf_to_speech_loader.py`
- Test: `test/unit/test_pdf_to_speech_loader.py`

**Step 1: Write the failing test**

```python
def test_create_tables_includes_title_column():
    """speakers 테이블에 title 컬럼이 포함되어야 함"""
    from modules.load.pdf_to_speech_loader import PDFToSpeechLoader
    import re
    import inspect
    source = inspect.getsource(PDFToSpeechLoader.create_table)
    assert "title TEXT" in source or "title text" in source.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest test/unit/test_pdf_to_speech_loader.py -v`
Expected: FAIL

**Step 3: Modify speakers table DDL**

In `modules/load/pdf_to_speech_loader.py`, update the CREATE TABLE statement for speakers:

```sql
CREATE TABLE IF NOT EXISTS speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Also add migration for existing tables:
```python
def create_table(self):
    # ... existing CREATE TABLE ...

    # Migration: add title column if not exists
    self._execute_query("""
        ALTER TABLE speakers ADD COLUMN IF NOT EXISTS title TEXT
    """)
```

Update the speaker upsert in `load()` to include title:
```python
self._execute_query(
    """INSERT INTO speakers (name, title) VALUES (%s, %s)
    ON CONFLICT (name) DO UPDATE SET title = EXCLUDED.title RETURNING id""",
    (name, speaker_title)
)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest test/unit/test_pdf_to_speech_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add modules/load/pdf_to_speech_loader.py test/unit/test_pdf_to_speech_loader.py
git commit -m "✨ Add: speakers 테이블에 title 컬럼 추가"
```

---

## Task 7: 전체 검증 및 최종 커밋

**Step 1: 전체 테스트 실행**

Run: `uv run pytest test/unit/ -v`
Expected: ALL PASS

**Step 2: 실제 PDF로 검증**

Run:
```bash
uv run python -c "
from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
import pdfplumber, warnings
warnings.filterwarnings('ignore')

t = PDFToSpeechTransformer()
with pdfplumber.open('제22대국회 제431회(임시회) 제1차 국회본회의(전체회의) (2026.01.15.).pdf') as pdf:
    text = '\n'.join(p.extract_text() for p in pdf.pages if p.extract_text())

speeches = t.transform(pdf_url_id='test', text=text, title='test', date='2026-01-15',
                        confer_number='1', dae_number='22', class_name='국회본회의', file_path='test')

print(f'Total speeches: {len(speeches)}')
unique_speakers = set()
for s in speeches:
    unique_speakers.add(f'{s[\"speaker_title\"]} {s[\"speaker\"]}')

print(f'Unique speakers: {len(unique_speakers)}')
for sp in sorted(unique_speakers):
    count = sum(1 for s in speeches if f'{s[\"speaker_title\"]} {s[\"speaker\"]}' == sp)
    print(f'  [{count:3d}] {sp}')
"
```

Expected:
- ~80 speeches (no false positives)
- Speakers: 우원식, 이학영, 이소희, 김호철, 한병도, 김상훈, 정태호, 황희, 양부남, 최보윤, 박정, 김은혜, 한준호, 이성윤, 천하람, 김승묵

**Step 3: Commit**

```bash
git add -A
git commit -m "🔧 Fix: 회의록 PDF 전처리 로직 전체 개선

- 페이지 헤더 자동 제거
- 부록 섹션 자동 감지 및 제거
- 비발언 항목 오탐 필터링 (의안명, 메타데이터)
- 발언 텍스트 노이즈 제거 (타임스탬프, 무대지시, 절차 메모)
- 발언자 직책/이름 분리
- speakers 테이블 title 컬럼 추가

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Verification

```bash
# 1. 단위 테스트
uv run pytest test/unit/test_transformers.py -v

# 2. 전체 테스트
uv run pytest test/unit/ -v

# 3. 실제 PDF 검증 (위 Task 7 Step 2 참조)

# 4. Git 상태
git status
git log --oneline -5
```

### 성공 기준

- [ ] False positive 0건 (비발언 항목 제거됨)
- [ ] 발언 텍스트에 페이지 헤더, 타임스탬프, 무대지시 없음
- [ ] 직책/이름 분리 동작 (speaker_title, speaker 별도 필드)
- [ ] speakers 테이블에 title 컬럼 존재
- [ ] 기존 테스트 + 신규 테스트 모두 통과
- [ ] 실제 PDF에서 ~80개 발언, ~16명 발언자 추출
