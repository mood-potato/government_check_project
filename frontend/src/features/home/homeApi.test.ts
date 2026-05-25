import { describe, expect, it } from "bun:test";

import { loadFeaturedMembers, loadHomeHero, loadHomePage, loadRecentCases } from "./homeApi";
import type { FeaturedMemberDto, HomeHeroDto, HomePageDto, RecentCaseDto } from "./types";

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

describe("home section loaders", () => {
  it("fetches the hero section from /api/home/hero", async () => {
    const hero: HomeHeroDto = {
      member: {
        id: "11111111-1111-1111-1111-111111111111",
        slug: "abc123-22",
        name: "강테스트",
        party_name: "테스트당",
        district_name: "서울 테스트구",
        profile_image_url: null
      },
      topic_label: "예산",
      topic_slug: "budget",
      past_speech: {
        spoken_date: "2024-01-01",
        meeting_name: "본회의",
        speech_text: "과거 발언",
        original_url: null
      },
      recent_speech: {
        spoken_date: "2026-01-01",
        meeting_name: "본회의",
        speech_text: "최근 발언",
        original_url: null
      },
      summary: "예산 관련 발언을 비교했습니다."
    };
    const calls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return Response.json(hero);
    };

    await expect(loadHomeHero(fetcher)).resolves.toEqual(hero);
    expect(calls).toEqual(["/api/home/hero"]);
  });

  it("fetches recent cases and featured members from separate endpoints", async () => {
    const recentCases: RecentCaseDto[] = [];
    const featuredMembers: FeaturedMemberDto[] = [];
    const calls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return Response.json(String(input).includes("recent-cases") ? recentCases : featuredMembers);
    };

    await expect(loadRecentCases(fetcher)).resolves.toEqual(recentCases);
    await expect(loadFeaturedMembers(fetcher)).resolves.toEqual(featuredMembers);
    expect(calls).toEqual(["/api/home/recent-cases", "/api/home/featured-members"]);
  });
});
