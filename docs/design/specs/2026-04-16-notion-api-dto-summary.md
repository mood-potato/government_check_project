# 홈 / 인물 상세 API + DTO 정리

작성일: 2026-04-16
수정일: 2026-04-20
상태: v1 초안

---

## 문서 목적

홈 화면과 인물 상세 페이지에서 사용할 `최소 DTO`를 정리한다.

DTO는 화면의 모든 UI 요소를 설명하는 객체가 아니라, API와 프론트엔드가 공유하는 `데이터 계약`이다.

이번 v1에서는 아래 두 엔드포인트만 우선 구현한다.

- `GET /api/home`
- `GET /api/members/{member_slug}`

---

## 명칭 원칙

- `StatementDto` 대신 `MemberSpeechDto`를 쓴다.
- `quote` 대신 `speech_text`를 쓴다.
- `source_url` 대신 `original_url`을 쓴다.
- `past_statement`, `recent_statement` 대신 `past_speech`, `recent_speech`를 쓴다.

이유: DTO 이름만 봐도 `특정 의원의 발언 데이터`라는 의미가 보여야 한다.

---

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

## 엔드포인트 연결

- `GET /api/home` -> `HomePageDto`
- `GET /api/members/{member_slug}` -> `MemberDetailDto`
