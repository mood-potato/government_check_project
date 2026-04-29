import { describe, expect, it } from "bun:test";

import { loadHomePage } from "./homeApi";
import type { HomePageDto } from "./types";

describe("loadHomePage", () => {
  it("fetches the home DTO from /api/home", async () => {
    const dto: HomePageDto = {
      hero: null,
      popular_keywords: [],
      recent_cases: [],
      featured_members: [
        {
          rank: 1,
          member: {
            id: "11111111-1111-1111-1111-111111111111",
            slug: "abc123-22",
            name: "강테스트",
            party_name: "테스트당",
            district_name: "서울 테스트구",
            profile_image_url: null
          },
          summary: "22대 테스트당 서울 테스트구"
        }
      ],
      disclaimer: "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
    };
    const calls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return new Response(JSON.stringify(dto), {
        headers: { "content-type": "application/json" }
      });
    };

    await expect(loadHomePage(fetcher)).resolves.toEqual(dto);
    expect(calls).toEqual(["/api/home"]);
  });

  it("raises a useful error when /api/home fails", async () => {
    const fetcher = async () => new Response("failed", { status: 503 });

    await expect(loadHomePage(fetcher)).rejects.toThrow("/api/home failed: 503");
  });
});
