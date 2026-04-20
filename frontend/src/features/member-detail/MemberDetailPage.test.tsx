import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { MemberDetailPage } from "./MemberDetailPage";
import { sampleMemberDetailPage } from "./sampleMemberDetailPage";

describe("MemberDetailPage", () => {
  it("renders the basic_detail.html inspired member profile screen from the detail DTO", () => {
    const html = renderToStaticMarkup(<MemberDetailPage data={sampleMemberDetailPage} />);

    expect(html).toContain("AssemblyVoice");
    expect(html).not.toContain('class="nav-links"');
    expect(html).not.toContain('class="nav-search"');
    expect(html).toContain("김서준 의원");
    expect(html).toContain("제22대 국회의원");
    expect(html).toContain("최근 2년간 부동산·노동 쟁점 회의에 반복적으로 참여한 의원");
    expect(html).toContain("자주 등장한 쟁점");
    expect(html).toContain("부동산 취득세");
    expect(html).toContain("이 사람이 자주 선 갈등");
    expect(html).toContain("상반 발언 분석");
    expect(html).toContain("2024년 1월 발언");
    expect(html).toContain("2026년 3월 발언");
    expect(html).toContain("참여 안건 기록");
    expect(html).toContain("논리가 유사한 의원");
    expect(html).toContain("주요 갈등 상대");
    expect(html).toContain("자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요.");
  });
});
