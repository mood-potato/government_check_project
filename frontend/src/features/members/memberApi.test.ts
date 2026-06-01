import { describe, expect, it } from "bun:test";

import { loadMemberDetail, loadMembers } from "./memberApi";
import type { MemberListPageDto } from "./types";
import type { MemberDetailPageDto } from "../member-detail/types";

describe("memberApi", () => {
  it("fetches the member list DTO from /api/members", async () => {
    const dto: MemberListPageDto = {
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
        }
      ],
      disclaimer: "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
    };
    const calls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return new Response(JSON.stringify(dto), {
        headers: { "content-type": "application/json" }
      });
    };

    await expect(loadMembers(fetcher)).resolves.toEqual(dto);
    expect(calls).toEqual(["/api/members"]);
  });

  it("fetches member detail by slug", async () => {
    const dto = {
      member: {
        id: "11111111-1111-1111-1111-111111111111",
        slug: "abc123-22",
        name: "강테스트",
        party_name: "테스트당",
        district_name: "서울 테스트구",
        profile_image_url: null,
        generation_label: "제22대 국회의원",
        committee_name: null,
        status_label: "지역구",
        fact_summary: "22대 테스트당 서울 테스트구 재선 의원"
      },
      metrics: [],
      conflicts: [],
      contradictory_speeches: [
        { label: "과거 발언", speech_text: "준비 중", source: "자동 분석 준비 중", tone: "past" },
        { label: "최근 발언", speech_text: "준비 중", source: "자동 분석 준비 중", tone: "recent" }
      ],
      recent_speeches: [],
      agendas: [],
      similar_members: [],
      opposing_members: [],
      disclaimer: "자동 분석 결과이며, 원문과 회의 맥락을 함께 확인하세요."
    } satisfies MemberDetailPageDto;
    const calls: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      calls.push(String(input));
      return new Response(JSON.stringify(dto), {
        headers: { "content-type": "application/json" }
      });
    };

    await expect(loadMemberDetail("abc123-22", fetcher)).resolves.toEqual(dto);
    expect(calls).toEqual(["/api/members/abc123-22"]);
  });

  it("raises useful errors when member endpoints fail", async () => {
    const fetcher = async () => new Response("failed", { status: 404 });

    await expect(loadMembers(fetcher)).rejects.toThrow("/api/members failed: 404");
    await expect(loadMemberDetail("missing-22", fetcher)).rejects.toThrow("/api/members/missing-22 failed: 404");
  });
});
