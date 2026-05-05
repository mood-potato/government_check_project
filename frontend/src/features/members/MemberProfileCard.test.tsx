import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { MemberProfileCard } from "./MemberProfileCard";

const member = {
  id: "11111111-1111-1111-1111-111111111111",
  slug: "abc123-22",
  name: "강테스트",
  party_name: "테스트당",
  district_name: "서울 테스트구",
  profile_image_url: "https://open.assembly.go.kr/photo.jpg"
};

describe("MemberProfileCard", () => {
  it("renders a linked member profile with a real profile image", () => {
    const html = renderToStaticMarkup(<MemberProfileCard member={member} summary="22대 테스트당 서울 테스트구" />);

    expect(html).toContain('href="/members/abc123-22"');
    expect(html).toContain('src="https://open.assembly.go.kr/photo.jpg"');
    expect(html).toContain('alt="강테스트 프로필"');
    expect(html).toContain("강테스트");
    expect(html).toContain("테스트당 · 서울 테스트구");
    expect(html).toContain("22대 테스트당 서울 테스트구");
  });

  it("renders a name initial fallback when the image is missing", () => {
    const html = renderToStaticMarkup(
      <MemberProfileCard member={{ ...member, profile_image_url: null }} summary="22대 테스트당 서울 테스트구" />
    );

    expect(html).not.toContain("<img");
    expect(html).toContain("member-avatar-fallback");
    expect(html).toContain("강");
  });
});
