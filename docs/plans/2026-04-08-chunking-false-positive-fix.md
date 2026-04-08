# PDF 청킹 오탐 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PDFToSpeechTransformer`에서 의안명이 발언자로 오탐되는 문제를 수정해 false positive를 0건으로 만든다.

**Architecture:** `◯`는 발언자와 의안명 모두에 쓰인다. 현재 `_is_non_speech`는 regex가 캡처한 2단어(speaker_raw)만 체크하므로, 법률안 이름의 "법률안"이 뒤에 붙는 경우를 놓친다. `transform`에서 speaker_raw + speech 앞부분(full_context)을 함께 `_is_non_speech`에 전달하도록 수정한다. 추가로, None speaker_title인 항목을 발언 목록에서 제거하는 안전망을 추가한다.

**Tech Stack:** Python 3.13, re, pytest

---

## 현재 오탐 목록 (실제 PDF 기준)

| speaker_raw (2단어) | 실제 전체 텍스트 |
|---|---|
| `노후계획도시 정비` | `◯노후계획도시 정비 및 지원에 관한 특별법 일부개정법률안` |
| `미세먼지 저감` | `◯미세먼지 저감 및 관리에 관한 특별법 일부개정법률안` |
| `자본시장과 금융투자업에` | `◯자본시장과 금융투자업에 관한 법률 일부개정법률안` |
| `재난 및` | `◯재난 및 안전관리 기본법 일부개정법률안` |
| `전기통신금융사기 피해` | `◯전기통신금융사기 피해 방지 및 피해금 환급에 관한 특별법 일부개정법률안` |

**공통 패턴:** regex가 2단어만 캡처하므로 `speaker_raw`에서는 "법률안"이 보이지 않음.
그러나 `speech`(group 2) 시작 부분에는 " 및 지원에 관한 특별법 일부개정법률안..."이 포함됨.

---

## 파일 구조

- `modules/transform/pdf_to_speech_transformer.py` — `_is_non_speech` 시그니처 + `transform` 호출부 수정
- `test/unit/test_transformers.py` — 5개 오탐 패턴 회귀 테스트 추가
- `test/conftest.py` — fixture 추가 (실제 오탐 패턴 포함)

---

## Task 1: `_is_non_speech`에 full_context 파라미터 추가

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py:93-101`
- Modify: `modules/transform/pdf_to_speech_transformer.py:159-165` (transform 호출부)
- Test: `test/unit/test_transformers.py`

- [ ] **Step 1: 회귀 테스트 작성 (먼저 실패해야 함)**

`test/unit/test_transformers.py`의 `TestNonSpeechFiltering` 클래스에 아래 테스트 추가:

```python
def test_filters_law_name_split_across_speaker_and_speech(self):
    """◯노후계획도시 정비 및 지원에 관한 특별법 일부개정법률안 패턴"""
    transformer = PDFToSpeechTransformer()
    # speaker_raw = "노후계획도시 정비"
    # speech_prefix = "및 지원에 관한 특별법 일부개정법률안"
    full_context = "노후계획도시 정비 및 지원에 관한 특별법 일부개정법률안"
    assert transformer._is_non_speech(full_context) is True

def test_filters_miryeongji_law(self):
    transformer = PDFToSpeechTransformer()
    full_context = "미세먼지 저감 및 관리에 관한 특별법 일부개정법률안"
    assert transformer._is_non_speech(full_context) is True

def test_filters_capital_market_law(self):
    transformer = PDFToSpeechTransformer()
    full_context = "자본시장과 금융투자업에 관한 법률 일부개정법률안"
    assert transformer._is_non_speech(full_context) is True

def test_filters_disaster_law(self):
    transformer = PDFToSpeechTransformer()
    full_context = "재난 및 안전관리 기본법 일부개정법률안"
    assert transformer._is_non_speech(full_context) is True

def test_filters_telecom_fraud_law(self):
    transformer = PDFToSpeechTransformer()
    full_context = "전기통신금융사기 피해 방지 및 피해금 환급에 관한 특별법 일부개정법률안"
    assert transformer._is_non_speech(full_context) is True
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest test/unit/test_transformers.py::TestNonSpeechFiltering -v
```

`test_filters_law_name_split_across_speaker_and_speech` 등 5개 FAIL 예상.
기존 4개 테스트는 PASS 유지 확인.

- [ ] **Step 3: `_is_non_speech` 수정 — 기존 2단어 체크는 유지, 법률안 패턴만 확장**

`modules/transform/pdf_to_speech_transformer.py:93-101`을 아래로 교체:

```python
def _is_non_speech(self, speaker_raw: str) -> bool:
    """비발언 항목인지 검사. speaker_raw는 2단어 fragment 또는 full_context 모두 가능."""
    for keyword in NON_SPEECH_KEYWORDS:
        if keyword in speaker_raw:
            return True
    # 법률안/의안명 패턴: "~법 일부개정법률안", "~법률안", "~법률 일부개정법률안"
    if re.search(r"법률?안|법률 일부개정|기본법 일부개정", speaker_raw):
        return True
    return False
```

- [ ] **Step 4: `transform`에서 full_context 전달**

`modules/transform/pdf_to_speech_transformer.py:159-165`를 아래로 교체:

```python
for idx, match in enumerate(self.speaker_pattern.finditer(text), start=1):
    speaker_raw = match.group(1).strip()
    speech = match.group(2).strip()

    # full_context = speaker_raw + speech 앞 80자 → 법률안 전체 이름이 보임
    full_context = speaker_raw + " " + speech[:80]
    if self._is_non_speech(full_context):
        continue
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
uv run pytest test/unit/test_transformers.py::TestNonSpeechFiltering -v
```

9개 모두 PASS 예상.

- [ ] **Step 6: 전체 테스트 회귀 확인**

```bash
uv run pytest test/unit/test_transformers.py -v
```

28개 → 33개 모두 PASS (기존 28 + 신규 5).

- [ ] **Step 7: 커밋**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "fix: 의안명 오탐 수정 — _is_non_speech에 full_context 전달"
```

---

## Task 2: speaker_title이 None인 항목 안전망 추가

**Files:**
- Modify: `modules/transform/pdf_to_speech_transformer.py` (transform 내부)
- Test: `test/unit/test_transformers.py`

speaker_title이 None이고 speaker_name이 알려진 이름 형식(2~4글자 한글)이 아닌 경우, 발언이 아닐 가능성이 높다. 이중 안전망으로 추가.

- [ ] **Step 1: 테스트 작성**

`test/unit/test_transformers.py`의 `TestNonSpeechFiltering`에 추가:

```python
def test_transform_excludes_entries_with_no_title_and_law_name_pattern(self):
    """법률 이름이 speaker로 파싱된 경우 transform 결과에서 제외"""
    transformer = PDFToSpeechTransformer()
    text = (
        "◯의장 우원식\n회의를 시작합니다.\n"
        "◯노후계획도시 정비\n및 지원에 관한 특별법 일부개정법률안(대안)\n"
        "◯이소희 의원\n찬성합니다.\n"
    )
    result = transformer.transform(
        pdf_url_id="test", text=text, title="테스트",
        date="2026-01-15", confer_number="1", dae_number="22",
        class_name="본회의", file_path="test.pdf",
    )
    speakers = [s["speaker"] for s in result]
    assert "정비" not in speakers  # "노후계획도시 정비" → speaker="정비" 로 파싱됨을 방지
    assert "우원식" in speakers
    assert "이소희" in speakers
    assert len(result) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
uv run pytest test/unit/test_transformers.py -k "test_transform_excludes_entries_with_no_title_and_law_name_pattern" -v
```

FAIL 예상 (Task 1 완료 후에는 이미 full_context 체크로 통과할 수 있음 — 통과하면 이 Task는 건너뜀).

- [ ] **Step 3: 통과 여부 확인 후 판단**

Task 1 수정만으로 통과하면 이 Task는 skip. 여전히 FAIL이면 아래 추가:

`transform` 내 `_parse_speaker` 호출 직후에:

```python
speaker_title, speaker_name = self._parse_speaker(speaker_raw)

# 안전망: 직책 없고 이름이 2~4글자 한글이 아니면 비발언 항목
if speaker_title is None:
    if not re.match(r"^[가-힣]{2,4}$", speaker_name):
        continue
```

- [ ] **Step 4: 전체 테스트 확인**

```bash
uv run pytest test/unit/test_transformers.py -v
```

전체 PASS.

- [ ] **Step 5: 커밋**

```bash
git add modules/transform/pdf_to_speech_transformer.py test/unit/test_transformers.py
git commit -m "fix: speaker_title None + 비한글이름 항목 추가 필터링"
```

---

## Task 3: 실제 PDF 검증

**Files:**
- 코드 변경 없음 — 검증만

- [ ] **Step 1: 실제 PDF 파싱 결과 확인**

```bash
uv run python -c "
from modules.transform.pdf_to_speech_transformer import PDFToSpeechTransformer
import pdfplumber, warnings
warnings.filterwarnings('ignore')

t = PDFToSpeechTransformer()
pdf_path = '제22대국회 제431회(임시회) 제1차 국회본회의(전체회의) (2026.01.15.).pdf'
with pdfplumber.open(pdf_path) as pdf:
    text = '\n'.join(p.extract_text() for p in pdf.pages if p.extract_text())

speeches = t.transform(
    pdf_url_id='test', text=text, title='test', date='2026-01-15',
    confer_number='1', dae_number='22', class_name='국회본회의', file_path='test'
)

print(f'Total speeches: {len(speeches)}')
false_positives = [s for s in speeches if s['speaker_title'] is None]
print(f'False positives (speaker_title=None): {len(false_positives)}')
for fp in false_positives:
    print(f'  - speaker_raw result: title={fp[\"speaker_title\"]}, name={fp[\"speaker\"]}')

unique_speakers = {}
for s in speeches:
    key = f'{s[\"speaker_title\"]} | {s[\"speaker\"]}'
    unique_speakers[key] = unique_speakers.get(key, 0) + 1

print()
print(f'Unique speakers: {len(unique_speakers)}')
for sp, count in sorted(unique_speakers.items()):
    print(f'  [{count:3d}] {sp}')
" 2>&1 | grep -v CropBox
```

- [ ] **Step 2: 성공 기준 확인**

| 항목 | 목표 | 확인 |
|---|---|---|
| False positives (speaker_title=None) | 0건 | |
| 의장 우원식 발언 수 | 30건 이상 | |
| 총 발언 수 | 60건 이상 | |
| 고유 발언자 | 15명 이상 | |

실패 시 → 나타난 false positive 패턴을 `NON_SPEECH_KEYWORDS`에 추가하거나 `_is_non_speech` 패턴 확장.

- [ ] **Step 3: 최종 커밋**

```bash
git add -A
git commit -m "fix: PDF 청킹 오탐 0건 달성 — 실제 PDF 검증 완료"
```

---

## Verification

```bash
# 단위 테스트
uv run pytest test/unit/test_transformers.py -v

# 전체 테스트
uv run pytest test/unit/ -v

# 실제 PDF 검증 (Task 3 Step 1)
```

### 성공 기준

- [ ] False positive 0건
- [ ] 기존 28개 테스트 전부 PASS
- [ ] 신규 테스트 6개 이상 PASS
- [ ] 실제 PDF에서 발언자 15명 이상, 총 발언 60건 이상
