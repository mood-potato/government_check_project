# Home / Member DTO Specification

**작성일:** 2026-04-16
**수정일:** 2026-04-20
**상태:** Draft
**범위:** 홈 화면, 인물 상세 페이지 v1 최소 DTO

---

## 1. 목적

이 문서는 홈 화면과 인물 상세 페이지에서 사용할 `최소 DTO`를 정의한다.

DTO는 화면의 모든 UI 요소를 설명하는 객체가 아니다.
DTO는 서버가 판단해서 내려줘야 하는 `데이터 계약`이다.

---

## 2. 명칭 원칙

이전 이름이 추상적이어서 아래처럼 더 직관적인 이름으로 바꾼다.

| 이전 이름 | 새 이름 | 이유 |
|---|---|---|
| `StatementDto` | `MemberSpeechDto` | `Statement`보다 `의원의 발언`이라는 의미가 명확함 |
| `date` | `spoken_date` | 날짜가 무엇의 날짜인지 명확히 함 |
| `quote` | `speech_text` | 화면에 보여줄 발언 텍스트라는 의미가 직접적임 |
| `source_url` | `original_url` | 원문 확인 링크라는 의미가 더 명확함 |
| `past_statement` | `past_speech` | 과거 발언이라는 의미가 명확함 |
| `recent_statement` | `recent_speech` | 최근 발언이라는 의미가 명확함 |

`MemberSpeechDto`는 전역 상태처럼 계속 들고 다니는 객체가 아니다.
비교 카드 안에서 `과거 발언 1개`, `최근 발언 1개`를 표현하기 위한 재사용 타입이다.

---

## 3. DTO에 넣는 것 / 빼는 것

DTO에 넣는다:

- DB 또는 분석 결과에서 나오는 데이터
- 서버가 선택한 대표 카드 / 추천 목록
- 발언일, 회의명, 짧은 발언 텍스트, 원문 링크
- AI 또는 분석 로직이 만든 요약 문장
- URL 식별자인 `slug`

DTO에서 뺀다:

- 고정 카피: `eyebrow`, `title`, `subtitle`
- 버튼 라벨
- 단순 라우팅 URL: `member_url`, `topic_url`
- 색상 토큰: `color`
- 고정 검색 옵션: `search.scopes`

---

## 4. 엔드포인트 연결

| Method | Path | 응답 DTO |
|---|---|---|
| `GET` | `/api/home` | `HomePageDto` |
| `GET` | `/api/members/{member_slug}` | `MemberDetailDto` |

---

## 5. 공통 설계 원칙

- 외부 URL 식별자는 `slug`를 사용한다.
- 내부 관계 식별자는 `id`를 유지한다.
- 날짜는 `YYYY-MM-DD` 문자열로 통일한다.
- 이미지 URL과 원문 URL은 nullable이다.
- 섹션 데이터가 없으면 에러 대신 빈 배열 `[]`을 반환한다.
- 홈 히어로가 없으면 `hero: null`을 반환한다.

---

## 6. DTO 정의

## ------------------ Home DTO / Python ------------------

```python
from pydantic import BaseModel


# 특정 의원의 화면용 발언 1개
class MemberSpeechDto(BaseModel):
    spoken_date: str
    meeting_name: str
    speech_text: str
    original_url: str | None = None


# 홈에서 사용하는 의원 참조 정보
class HomeMemberRefDto(BaseModel):
    id: str
    slug: str
    name: str
    party_name: str | None = None
    district_name: str | None = None
    profile_image_url: str | None = None


# 홈 메인 히어로 카드 데이터
class HomeHeroDto(BaseModel):
    member: HomeMemberRefDto
    topic_label: str
    topic_slug: str | None = None
    past_speech: MemberSpeechDto
    recent_speech: MemberSpeechDto
    summary: str


# 인기 검색 키워드
class PopularKeywordDto(BaseModel):
    label: str
    slug: str


# 추가 분석 사례 카드
class RecentCaseDto(BaseModel):
    id: str
    member: HomeMemberRefDto
    topic_label: str
    summary: str


# 지금 주목받는 인물 카드
class FeaturedMemberDto(BaseModel):
    rank: int
    member: HomeMemberRefDto
    summary: str


# 홈 화면 전체 응답
class HomePageDto(BaseModel):
    hero: HomeHeroDto | None = None
    popular_keywords: list[PopularKeywordDto]
    recent_cases: list[RecentCaseDto]
    featured_members: list[FeaturedMemberDto]
    disclaimer: str
```

---

## ------------------ Home DTO / TypeScript ------------------

```ts
// 특정 의원의 화면용 발언 1개
export type MemberSpeechDto = {
  spoken_date: string;
  meeting_name: string;
  speech_text: string;
  original_url: string | null;
};

// 홈에서 사용하는 의원 참조 정보
export type HomeMemberRefDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};

// 홈 메인 히어로 카드 데이터
export type HomeHeroDto = {
  member: HomeMemberRefDto;
  topic_label: string;
  topic_slug: string | null;
  past_speech: MemberSpeechDto;
  recent_speech: MemberSpeechDto;
  summary: string;
};

// 인기 검색 키워드
export type PopularKeywordDto = {
  label: string;
  slug: string;
};

// 추가 분석 사례 카드
export type RecentCaseDto = {
  id: string;
  member: HomeMemberRefDto;
  topic_label: string;
  summary: string;
};

// 지금 주목받는 인물 카드
export type FeaturedMemberDto = {
  rank: number;
  member: HomeMemberRefDto;
  summary: string;
};

// 홈 화면 전체 응답
export type HomePageDto = {
  hero: HomeHeroDto | null;
  popular_keywords: PopularKeywordDto[];
  recent_cases: RecentCaseDto[];
  featured_members: FeaturedMemberDto[];
  disclaimer: string;
};
```

---

## ------------------ Member DTO / Python ------------------

```python
from pydantic import BaseModel


# 특정 의원의 화면용 발언 1개
class MemberSpeechDto(BaseModel):
    spoken_date: str
    meeting_name: str
    speech_text: str
    original_url: str | None = None


# 인물 상세에서 사용하는 의원 참조 정보
class MemberRefDto(BaseModel):
    id: str
    slug: str
    name: str
    party_name: str | None = None
    district_name: str | None = None
    profile_image_url: str | None = None


# 인물 상세 프로필 정보
class MemberProfileDto(MemberRefDto):
    committee_name: str | None = None
    description: str


# 상단 요약 숫자
class MemberSummaryDto(BaseModel):
    issue_count: int
    meeting_count: int
    comparison_count: int


# 자주 선 갈등 카드
class ConflictDto(BaseModel):
    topic_label: str
    meeting_name: str
    spoken_date: str
    summary: str
    speech_text: str
    original_url: str | None = None


# 상반 발언 후보 카드
class ComparisonDto(BaseModel):
    past_speech: MemberSpeechDto
    recent_speech: MemberSpeechDto
    summary: str


# 참여 안건 카드
class BillDto(BaseModel):
    name: str
    latest_mentioned_at: str | None = None
    summary: str
    url: str | None = None


# 인물 상세 전체 응답
class MemberDetailDto(BaseModel):
    member: MemberProfileDto
    summary: MemberSummaryDto
    conflicts: list[ConflictDto]
    comparisons: list[ComparisonDto]
    bills: list[BillDto]
    similar_members: list[MemberRefDto]
    rival_members: list[MemberRefDto]
    disclaimer: str
```

---

## ------------------ Member DTO / TypeScript ------------------

```ts
// 특정 의원의 화면용 발언 1개
export type MemberSpeechDto = {
  spoken_date: string;
  meeting_name: string;
  speech_text: string;
  original_url: string | null;
};

// 인물 상세에서 사용하는 의원 참조 정보
export type MemberRefDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};

// 인물 상세 프로필 정보
export type MemberProfileDto = MemberRefDto & {
  committee_name: string | null;
  description: string;
};

// 상단 요약 숫자
export type MemberSummaryDto = {
  issue_count: number;
  meeting_count: number;
  comparison_count: number;
};

// 자주 선 갈등 카드
export type ConflictDto = {
  topic_label: string;
  meeting_name: string;
  spoken_date: string;
  summary: string;
  speech_text: string;
  original_url: string | null;
};

// 상반 발언 후보 카드
export type ComparisonDto = {
  past_speech: MemberSpeechDto;
  recent_speech: MemberSpeechDto;
  summary: string;
};

// 참여 안건 카드
export type BillDto = {
  name: string;
  latest_mentioned_at: string | null;
  summary: string;
  url: string | null;
};

// 인물 상세 전체 응답
export type MemberDetailDto = {
  member: MemberProfileDto;
  summary: MemberSummaryDto;
  conflicts: ConflictDto[];
  comparisons: ComparisonDto[];
  bills: BillDto[];
  similar_members: MemberRefDto[];
  rival_members: MemberRefDto[];
  disclaimer: string;
};
```

---

## 7. 파일 구조 추천

### Python

- `api/schemas/home.py`
- `api/schemas/member.py`

### TypeScript

- `frontend/src/features/home/types.ts`
- `frontend/src/features/member/types.ts`
