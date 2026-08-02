# Frontend Agent Overview

## Role

이 디렉터리는 AssemblyVoice의 화면 구현을 담당한다. 백엔드나 데이터 파이프라인을 직접 조립하지 않고, 화면 단위 DTO를 받아 홈과 인물 상세 화면을 렌더링하는 것이 기본 책임이다.

## Stack

- Runtime and tooling: Bun
- UI library: React
- Entry point: `src/main.tsx`
- App router: `src/App.tsx`
- Development server: `src/server.ts`
- Global styles: `src/styles.css`

Node.js, npm, pnpm, Vite, Express 대신 Bun 기반 명령과 `Bun.serve()`를 사용한다.

## Main Screens

- Home: `src/features/home/HomePage.tsx`
  - 가장 최근의 상반 발언 후보 1건을 중심으로 보여준다.
  - 검색은 첫 화면에서 바로 발견 가능해야 한다.
  - 불필요한 메뉴나 토픽 노출보다 핵심 비교 카드의 가독성을 우선한다.
- Member detail: `src/features/member-detail/MemberDetailPage.tsx`
  - 인물 프로필, 주요 지표, 갈등 기록, 상반 발언 분석, 참여 안건, 관련 인물을 순서대로 보여준다.
  - 표현은 평가형보다 사실형과 원문 확인 중심으로 유지한다.
- Member list: `src/features/members/MemberListPage.tsx`
  - 얼굴/이름/정당/선거구 기준 국회의원 프로필 그리드. `MemberProfileCard`를 카드 단위로 반복 렌더링한다.

## Data Shape

프론트엔드는 DB 테이블 구조를 직접 추측하지 않는다. 각 화면은 `types.ts`에 정의된 DTO를 기준으로 렌더링하고, 샘플 데이터는 같은 feature 폴더의 `sample*.ts` 파일에 둔다.

화면 계약을 바꿀 때는 다음을 함께 갱신한다.

- feature별 `types.ts`
- sample DTO
- 해당 화면 테스트

## Styling Principles

- 전역 스타일은 `src/styles.css`에 둔다.
- 카드, 버튼, 입력창은 8px radius 범위를 유지한다.
- 홈 첫 화면은 `최근 포착된 상반 발언 후보`와 검색을 빠르게 이해할 수 있어야 한다.
- 헤더는 고정 상태를 유지하되, 메뉴를 과하게 늘리지 않는다.
- 모바일에서도 텍스트가 버튼이나 카드 영역을 넘치지 않게 한다.

## Commands

```bash
bun install
bun run dev
bun test
bun run build
```

기본 개발 서버 포트는 `3000`이며, 이미 사용 중이면 `PORT=3001 bun run dev`처럼 포트를 지정한다.

## Testing

테스트는 `bun:test`를 사용한다.

- 화면 렌더링 테스트: 각 feature의 `*.test.tsx`
- 라우팅 테스트: `src/App.test.tsx`
- 스타일 가드 테스트: `src/styles.test.ts`

UI 구조를 줄이거나 이동할 때는 마크업 테스트와 스타일 가드 테스트를 함께 갱신한다.
