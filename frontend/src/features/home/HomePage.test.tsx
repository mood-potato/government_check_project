import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { HomePage } from "./HomePage";
import { sampleHomePage } from "./sampleHomePage";

describe("HomePage", () => {
  it("renders the home.html inspired AssemblyVoice landing screen from the home DTO", () => {
    const html = renderToStaticMarkup(<HomePage data={sampleHomePage} />);

    expect(html).toContain("AssemblyVoice");
    expect(html).toContain("DEMOCRACY IS YOUR VOICE HEARD");
    expect(html).toContain("최근 포착된");
    expect(html).toContain("상반 발언");
    expect(html).toContain("의원 이름이나 쟁점으로 검색");
    expect(html).toContain('class="hero-search"');
    expect(html).not.toContain("Hot Topics:");
    expect(html).not.toContain('class="nav-links"');
    expect(html).not.toContain('class="nav-search"');
    expect(html).toContain("최근 업데이트");
    expect(html).toContain("자동 분석");
    expect(html).toContain("김태호 의원");
    expect(html).toContain("2024.02.03 발췌");
    expect(html).toContain("2026.02.03 발췌");
    expect(html).toContain("원문 보기");
    expect(html).toContain("이 주제 더 보기");
    expect(html).toContain("추가 분석 사례");
    expect(html).toContain("지금 주목받는 인물");
    expect(html).toContain("자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요.");
  });
});
