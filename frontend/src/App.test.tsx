import { describe, expect, it } from "bun:test";
import { renderToStaticMarkup } from "react-dom/server";

import { App } from "./App";

describe("App routing", () => {
  it("renders the member detail loading state for member routes", () => {
    const html = renderToStaticMarkup(<App path="/members/kim-seo-jun" />);

    expect(html).toContain("의원 정보를 불러오는 중입니다.");
  });

  it("renders the member list loading state for /members", () => {
    const html = renderToStaticMarkup(<App path="/members" />);

    expect(html).toContain("국회의원 프로필을 불러오는 중입니다.");
  });
});
