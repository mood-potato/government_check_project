# Home / Member DTO Specification

**작성일:** 2026-04-16
**상태:** Draft
**범위:** 홈 화면, 인물 상세 페이지 v1 API DTO

---

## 1. 목적

이 문서는 React 프런트엔드와 FastAPI 백엔드가 공유할 `화면 단위 DTO`를 정의한다.

이번 v1 범위는 아래 두 엔드포인트다.

- `GET /api/home`
- `GET /api/members/{member_slug}`

핵심 원칙:

- 프런트엔드가 DB 테이블 구조를 직접 조립하지 않는다.
- API는 `페이지 렌더링에 필요한 형태`로 가공된 DTO를 반환한다.
- 대외 표현은 `모순`보다 `상반 발언 후보`, `자동 분석`, `원문 확인` 같은 중립 표현을 우선한다.

---

## 2. 엔드포인트 요약

| Method | Path | 목적 | 응답 DTO |
|---|---|---|---|
| `GET` | `/api/home` | 홈 화면 전체 렌더링용 데이터 반환 | `HomePageDto` |
| `GET` | `/api/members/{member_slug}` | 인물 상세 전체 렌더링용 데이터 반환 | `MemberDetailDto` |

외부 URL 식별자는 `slug`를 사용한다.
내부 참조와 관계 연결은 `id`를 유지한다.

---

## 3. DTO 설계 원칙

### 3.1 필드 원칙

- 날짜는 모두 `YYYY-MM-DD` 문자열로 통일한다.
- 이미지 URL과 원문 URL은 없을 수 있으므로 nullable 허용이 가능해야 한다.
- 섹션 데이터가 없을 때는 에러 대신 빈 배열을 우선 사용한다.
- `member_slug`는 URL용 식별자이고, `member.id`는 내부 식별자다.

### 3.2 홈 화면 원칙

- 홈은 `히어로 카드 1개`가 중심이다.
- 홈 응답은 페이지 전체를 위한 DTO로 설계한다.
- 하지만 정적 UI까지 과하게 API에 넣지 않는다.

### 3.3 인물 상세 원칙

- 인물 상세는 `프로필 중심`이다.
- 정보 흐름은 `인물 소개 -> 자주 선 갈등 -> 상반 발언 후보 -> 참여 안건 -> 비슷한 의원 / 상대 의원` 순서다.

---

## 4. GET `/api/home`

### 4.1 목적

홈 화면 전체 렌더링용 데이터 반환.

### 4.2 응답 구조

```ts
type HomePageDto = {
  hero: HomeHeroDto | null;
  search: HomeSearchDto;
  popular_keywords: PopularKeywordDto[];
  recent_cases: RecentCaseDto[];
  featured_members: FeaturedMemberDto[];
  disclaimer: string;
};
```

### 4.3 필드 정의

#### `HomePageDto`

| 필드 | 타입 | 설명 |
|---|---|---|
| `hero` | `HomeHeroDto \| null` | 홈 메인 히어로 카드 |
| `search` | `HomeSearchDto` | 검색 바 설정 |
| `popular_keywords` | `PopularKeywordDto[]` | 인기 검색 키워드 칩 |
| `recent_cases` | `RecentCaseDto[]` | 추가 분석 사례 카드 |
| `featured_members` | `FeaturedMemberDto[]` | 지금 주목받는 인물 리스트 |
| `disclaimer` | `string` | 자동 분석 안내 문구 |

#### `HomeHeroDto`

```ts
type HomeHeroDto = {
  eyebrow: string;
  title: string;
  subtitle: string;
  member: HomeHeroMemberDto;
  badges: string[];
  comparison: HeroComparisonDto;
  actions: HeroActionsDto;
};
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `eyebrow` | `string` | 히어로 상단 라벨 |
| `title` | `string` | 메인 타이틀 |
| `subtitle` | `string` | 설명 문장 |
| `member` | `HomeHeroMemberDto` | 대표 의원 정보 |
| `badges` | `string[]` | `최근 업데이트`, `자동 분석`, `부동산` 같은 배지 |
| `comparison` | `HeroComparisonDto` | 좌우 발언 비교 데이터 |
| `actions` | `HeroActionsDto` | CTA 링크 |

#### `HomeHeroMemberDto`

```ts
type HomeHeroMemberDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};
```

#### `HeroComparisonDto`

```ts
type HeroComparisonDto = {
  past_statement: StatementDto;
  recent_statement: StatementDto;
  summary_quote: string;
};
```

#### `StatementDto`

```ts
type StatementDto = {
  date: string;
  meeting_name: string;
  quote: string;
  source_url: string | null;
};
```

#### `HeroActionsDto`

```ts
type HeroActionsDto = {
  member_url: string;
  topic_url: string;
};
```

#### `HomeSearchDto`

```ts
type HomeSearchDto = {
  scopes: SearchScopeDto[];
  default_scope: string;
  placeholder: string;
};
```

#### `SearchScopeDto`

```ts
type SearchScopeDto = {
  value: string;
  label: string;
};
```

#### `PopularKeywordDto`

```ts
type PopularKeywordDto = {
  keyword: string;
  color: string;
  url: string;
};
```

#### `RecentCaseDto`

```ts
type RecentCaseDto = {
  case_id: string;
  member: SimpleMemberDto;
  topic_label: string;
  date_range_label: string;
  summary: string;
  member_url: string;
};
```

#### `FeaturedMemberDto`

```ts
type FeaturedMemberDto = {
  rank: number;
  member: SimpleMemberDto;
  issue_summary: string;
  member_url: string;
};
```

#### `SimpleMemberDto`

```ts
type SimpleMemberDto = {
  id: string;
  slug: string;
  name: string;
  profile_image_url: string | null;
};
```

### 4.4 응답 예시

```json
{
  "hero": {
    "eyebrow": "DEMOCRACY IS YOUR VOICE HEARD",
    "title": "최근 포착된 상반 발언 후보",
    "subtitle": "투표 전에, 지금 비교해보세요. AssemblyVoice가 인공지능으로 공직자의 발언 일관성을 투명하게 분석합니다.",
    "member": {
      "id": "member_123",
      "slug": "kim-tae-hoon",
      "name": "김태훈 의원",
      "party_name": "대한민국당",
      "district_name": "서울 종로구",
      "profile_image_url": "/assets/members/member_123.png"
    },
    "badges": ["최근 업데이트", "자동 분석", "부동산"],
    "comparison": {
      "past_statement": {
        "date": "2024-02-03",
        "meeting_name": "본회의",
        "quote": "이런 거 아니에요.",
        "source_url": "https://example.com/speech/1001"
      },
      "recent_statement": {
        "date": "2026-02-03",
        "meeting_name": "본회의",
        "quote": "이런 거예요.",
        "source_url": "https://example.com/speech/2001"
      },
      "summary_quote": "주택 공급 안정을 위해 규제 완화가 필수적이라고 2년 전 말한 의원과 달리, 최근 토론회에서는 투기 방지를 위한 강력한 규제 유지를 주장하고 있습니다."
    },
    "actions": {
      "member_url": "/members/kim-tae-hoon",
      "topic_url": "/topics/real-estate"
    }
  },
  "search": {
    "scopes": [
      { "value": "all", "label": "전체 검색" },
      { "value": "member", "label": "의원 검색" },
      { "value": "speech", "label": "발언 검색" },
      { "value": "bill", "label": "안건 검색" }
    ],
    "default_scope": "all",
    "placeholder": "이슈, 의원, 발언의 원문을 검색해보세요..."
  },
  "popular_keywords": [
    { "keyword": "부동산", "color": "red", "url": "/search?q=부동산" },
    { "keyword": "교육", "color": "blue", "url": "/search?q=교육" }
  ],
  "recent_cases": [
    {
      "case_id": "case_1",
      "member": {
        "id": "member_201",
        "slug": "park-min-su",
        "name": "박민수 의원",
        "profile_image_url": "/assets/members/member_201.png"
      },
      "topic_label": "교육",
      "date_range_label": "교직정책 / 2023-2024",
      "summary": "입시 제도 개편에 대해 한편으론 유지에서 전면 개편으로 입장을 선회했습니다.",
      "member_url": "/members/park-min-su"
    }
  ],
  "featured_members": [
    {
      "rank": 1,
      "member": {
        "id": "member_301",
        "slug": "han-ji-hoon",
        "name": "한지훈",
        "profile_image_url": "/assets/members/member_301.png"
      },
      "issue_summary": "언급 이슈: 국민연금 개편, 저출산 대책",
      "member_url": "/members/han-ji-hoon"
    }
  ],
  "disclaimer": "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
}
```

### 4.5 빈 상태

- `hero`가 없으면 `null`
- `popular_keywords`, `recent_cases`, `featured_members`는 데이터 없을 때 `[]`

---

## 5. GET `/api/members/{member_slug}`

### 5.1 목적

인물 상세 페이지 전체 렌더링용 데이터 반환.

### 5.2 응답 구조

```ts
type MemberDetailDto = {
  member: MemberProfileDto;
  summary: MemberSummaryDto;
  conflict_highlights: ConflictHighlightDto[];
  comparison_candidates: ComparisonCandidateDto[];
  bills: BillDto[];
  similar_members: RelatedMemberDto[];
  rival_members: RelatedMemberDto[];
  disclaimer: string;
};
```

### 5.3 필드 정의

#### `MemberProfileDto`

```ts
type MemberProfileDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  committee_name: string | null;
  profile_image_url: string | null;
  description: string;
};
```

#### `MemberSummaryDto`

```ts
type MemberSummaryDto = {
  issue_count: number;
  meeting_count: number;
  comparison_count: number;
};
```

#### `ConflictHighlightDto`

```ts
type ConflictHighlightDto = {
  topic_label: string;
  meeting_name: string;
  date: string;
  conflict_summary: string;
  quote: string;
  source_url: string | null;
};
```

#### `ComparisonCandidateDto`

```ts
type ComparisonCandidateDto = {
  past_statement: StatementDto;
  recent_statement: StatementDto;
};
```

#### `BillDto`

```ts
type BillDto = {
  bill_name: string;
  latest_mentioned_at: string | null;
  stance_summary: string;
  bill_url: string | null;
};
```

#### `RelatedMemberDto`

```ts
type RelatedMemberDto = {
  member_id: string;
  member_slug: string;
  name: string;
  profile_image_url: string | null;
};
```

### 5.4 응답 예시

```json
{
  "member": {
    "id": "member_123",
    "slug": "kim-tae-hoon",
    "name": "김태훈 의원",
    "party_name": "대한민국당",
    "district_name": "서울 종로구",
    "committee_name": "국토교통위원회",
    "profile_image_url": "/assets/members/member_123.png",
    "description": "최근 2년간 부동산·노동 쟁점 회의에 반복적으로 참여한 의원"
  },
  "summary": {
    "issue_count": 4,
    "meeting_count": 28,
    "comparison_count": 3
  },
  "conflict_highlights": [
    {
      "topic_label": "부동산 규제",
      "meeting_name": "국토교통위원회 전체회의",
      "date": "2026-02-03",
      "conflict_summary": "공급 확대와 규제 강화 방향을 두고 충돌",
      "quote": "시장 안정만으로는 해결되지 않습니다.",
      "source_url": "https://example.com/speech/2001"
    }
  ],
  "comparison_candidates": [
    {
      "past_statement": {
        "date": "2024-02-03",
        "meeting_name": "국토교통위원회 전체회의",
        "quote": "이런 거 아니에요.",
        "source_url": "https://example.com/speech/1001"
      },
      "recent_statement": {
        "date": "2026-02-03",
        "meeting_name": "본회의",
        "quote": "이런 거예요.",
        "source_url": "https://example.com/speech/2001"
      }
    }
  ],
  "bills": [
    {
      "bill_name": "전세사기특별법 개정안",
      "latest_mentioned_at": "2026-01-12",
      "stance_summary": "보완 입법 필요성을 반복적으로 언급",
      "bill_url": "https://example.com/bills/1"
    }
  ],
  "similar_members": [
    {
      "member_id": "member_200",
      "member_slug": "kim-oo",
      "name": "김OO",
      "profile_image_url": "/assets/members/member_200.jpg"
    }
  ],
  "rival_members": [
    {
      "member_id": "member_300",
      "member_slug": "lee-oo",
      "name": "이OO",
      "profile_image_url": "/assets/members/member_300.jpg"
    }
  ],
  "disclaimer": "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
}
```

### 5.5 에러 및 빈 상태

- `member_slug`가 없으면 `404 Not Found`
- `conflict_highlights`, `comparison_candidates`, `bills`, `similar_members`, `rival_members`는 데이터 없을 때 `[]`

---

## 6. Pydantic 모델 초안

```python
from pydantic import BaseModel


class StatementDto(BaseModel):
    date: str
    meeting_name: str
    quote: str
    source_url: str | None = None


class SimpleMemberDto(BaseModel):
    id: str
    slug: str
    name: str
    profile_image_url: str | None = None


class HomeHeroMemberDto(SimpleMemberDto):
    party_name: str | None = None
    district_name: str | None = None


class HeroComparisonDto(BaseModel):
    past_statement: StatementDto
    recent_statement: StatementDto
    summary_quote: str


class HeroActionsDto(BaseModel):
    member_url: str
    topic_url: str


class HomeHeroDto(BaseModel):
    eyebrow: str
    title: str
    subtitle: str
    member: HomeHeroMemberDto
    badges: list[str]
    comparison: HeroComparisonDto
    actions: HeroActionsDto


class SearchScopeDto(BaseModel):
    value: str
    label: str


class HomeSearchDto(BaseModel):
    scopes: list[SearchScopeDto]
    default_scope: str
    placeholder: str


class PopularKeywordDto(BaseModel):
    keyword: str
    color: str
    url: str


class RecentCaseDto(BaseModel):
    case_id: str
    member: SimpleMemberDto
    topic_label: str
    date_range_label: str
    summary: str
    member_url: str


class FeaturedMemberDto(BaseModel):
    rank: int
    member: SimpleMemberDto
    issue_summary: str
    member_url: str


class HomePageDto(BaseModel):
    hero: HomeHeroDto | None = None
    search: HomeSearchDto
    popular_keywords: list[PopularKeywordDto]
    recent_cases: list[RecentCaseDto]
    featured_members: list[FeaturedMemberDto]
    disclaimer: str


class MemberProfileDto(BaseModel):
    id: str
    slug: str
    name: str
    party_name: str | None = None
    district_name: str | None = None
    committee_name: str | None = None
    profile_image_url: str | None = None
    description: str


class MemberSummaryDto(BaseModel):
    issue_count: int
    meeting_count: int
    comparison_count: int


class ConflictHighlightDto(BaseModel):
    topic_label: str
    meeting_name: str
    date: str
    conflict_summary: str
    quote: str
    source_url: str | None = None


class ComparisonCandidateDto(BaseModel):
    past_statement: StatementDto
    recent_statement: StatementDto


class BillDto(BaseModel):
    bill_name: str
    latest_mentioned_at: str | None = None
    stance_summary: str
    bill_url: str | None = None


class RelatedMemberDto(BaseModel):
    member_id: str
    member_slug: str
    name: str
    profile_image_url: str | None = None


class MemberDetailDto(BaseModel):
    member: MemberProfileDto
    summary: MemberSummaryDto
    conflict_highlights: list[ConflictHighlightDto]
    comparison_candidates: list[ComparisonCandidateDto]
    bills: list[BillDto]
    similar_members: list[RelatedMemberDto]
    rival_members: list[RelatedMemberDto]
    disclaimer: str
```

---

## 7. 구현 순서 제안

1. `api/schemas/` 또는 `api/schemas.py`에 Pydantic DTO 정의
2. `GET /api/home` route stub 추가
3. `GET /api/members/{member_slug}` route stub 추가
4. mock 데이터로 React 화면 연결
5. 이후 서비스 레이어에서 실제 DB 조립 로직 구현

---

## 8. 보류 항목

- `hot_topics`, `recent_members`를 `GET /api/home` 응답에 추가할지 여부
- `topic_url` 전용 토픽 페이지를 만들지 여부
- `member_slug` 생성 규칙의 장기 정책
- 홈 히어로가 없을 때 `hero: null`로 통일할지 여부
