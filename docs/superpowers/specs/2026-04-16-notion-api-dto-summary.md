# 홈 / 인물 상세 API + DTO 정리

작성일: 2026-04-16
상태: v1 초안

---

## 문서 목적

이 문서는 홈 화면과 인물 상세 페이지를 구현하기 위한 v1 API / DTO 기준선을 정리한 문서다.

이번 단계에서는 아래 두 엔드포인트만 우선 구현한다.

- `GET /api/home`
- `GET /api/members/{member_slug}`

핵심 원칙은 하나다.

`프런트엔드가 DB 구조를 직접 조립하지 않고, 화면에 필요한 형태로 가공된 DTO를 API가 반환한다.`

---

## 제품 방향

- 이 서비스는 단순 회의록 검색기가 아니라, 유권자가 투표 전에 공직자의 판단 패턴을 읽는 서비스다.
- 홈 화면의 핵심 경험은 `최근 포착된 상반 발언 후보`를 빠르게 비교하게 만드는 것이다.
- 인물 상세는 `프로필 중심`으로 구성하고, 그 사람이 `어떤 갈등에 자주 서는지`를 먼저 보여준다.
- 표현은 `모순`보다 `상반 발언 후보`, `자동 분석`, `원문 확인` 같은 중립 용어를 우선 사용한다.

---

## v1 엔드포인트

| Method | Path | 목적 | 응답 DTO |
| --- | --- | --- | --- |
| GET | `/api/home` | 홈 화면 전체 렌더링 데이터 | `HomePageDto` |
| GET | `/api/members/{member_slug}` | 인물 상세 전체 렌더링 데이터 | `MemberDetailDto` |

외부 URL 식별자는 `slug`를 사용한다.
내부 참조는 `id`를 유지한다.

---

## 1. GET `/api/home`

### 목적

홈 화면 전체 데이터를 한 번에 반환한다.

### 포함 섹션

- 히어로 카드
- 검색 바 설정
- 인기 검색 키워드
- 추가 분석 사례
- 지금 주목받는 인물
- 자동 분석 안내 문구

### 응답 구조

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

### 홈 DTO 상세

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

### 홈 응답 예시

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
      "summary_quote": "2년 전과 최근의 발언을 비교했을 때, 같은 이슈에 대한 판단 방향이 달라진 사례입니다."
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
  "recent_cases": [],
  "featured_members": [],
  "disclaimer": "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
}
```

### 홈 응답 원칙

- `hero`는 없을 수 있으므로 `null` 허용
- 리스트 데이터는 없을 때 `[]`
- 홈은 페이지 단위 응답으로 구성하되, 정적인 UI 문자열은 과하게 API에 넣지 않는다

---

## 2. GET `/api/members/{member_slug}`

### 목적

인물 상세 페이지 전체 데이터를 한 번에 반환한다.

### 포함 섹션

- 프로필
- 요약 수치
- 자주 선 갈등
- 상반 발언 후보
- 참여 안건
- 비슷한 국회의원
- 상대 국회의원
- 자동 분석 안내 문구

### 응답 구조

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

### 인물 상세 DTO 상세

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

### 인물 상세 응답 예시

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

### 인물 상세 응답 원칙

- `member_slug`가 유효하지 않으면 `404`
- 섹션 데이터가 없을 때는 빈 배열 사용
- 설명 문구는 평가형보다 사실형 우선

---

## 구현 결론

이번 v1에서 먼저 할 일:

1. `api/schemas.py` 또는 `api/schemas/`에 DTO 정의
2. `GET /api/home` route stub 추가
3. `GET /api/members/{member_slug}` route stub 추가
4. mock 응답으로 React 화면 연결
5. 이후 실제 서비스 로직 연결

이번 단계에서 보류하는 것:

- 홈을 `/api/home/hero`, `/api/home/recent`처럼 더 세분화하는 일
- 인물 상세를 `/summary`, `/conflicts`, `/bills` 등으로 쪼개는 일
- slug의 장기 운영 정책

지금은 `페이지 단위 DTO`가 우선이다.
