import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { App } from "./App";

describe("App routing", () => {
  it("renders the member detail page for member routes", () => {
    const html = renderToStaticMarkup(<App path="/members/kim-seo-jun" />);

    expect(html).toContain("김서준 의원");
    expect(html).toContain("Active Member");
    expect(html).toContain("최근 발언 보기");
    expect(html).toContain("자주 선 갈등");
    expect(html).toContain("상반 발언 분석");
    expect(html).toContain("참여 안건 기록");
    expect(html).toContain("논리가 유사한 의원");
    expect(html).toContain("주요 갈등 상대");
    expect(html).toContain("자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요.");
  });
});
