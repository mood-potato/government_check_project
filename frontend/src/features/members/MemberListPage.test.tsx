import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { MemberListPage } from "./MemberListPage";
import type { MemberListPageDto } from "./types";

const data: MemberListPageDto = {
  items: [
    {
      member: {
        id: "11111111-1111-1111-1111-111111111111",
        slug: "abc123-22",
        name: "강테스트",
        party_name: "테스트당",
        district_name: "서울 테스트구",
        profile_image_url: "https://open.assembly.go.kr/photo.jpg"
      },
      summary: "22대 테스트당 서울 테스트구"
    },
    {
      member: {
        id: "22222222-2222-2222-2222-222222222222",
        slug: "xyz789-18",
        name: "비례테스트",
        party_name: "예시당",
        district_name: null,
        profile_image_url: null
      },
      summary: "18대 예시당"
    }
  ],
  disclaimer: "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
};

describe("MemberListPage", () => {
  it("renders every member profile from the list DTO", () => {
    const html = renderToStaticMarkup(<MemberListPage data={data} />);

    expect(html).toContain("국회의원 프로필");
    expect(html).toContain("강테스트");
    expect(html).toContain("비례테스트");
    expect(html).toContain('href="/members/abc123-22"');
    expect(html).toContain('href="/members/xyz789-18"');
    expect(html).toContain("자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요.");
  });
});
