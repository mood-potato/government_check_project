import type { MemberDetailPageDto } from "../member-detail/types";
import type { MemberListPageDto } from "./types";

export async function loadMembers(fetcher: typeof fetch = fetch): Promise<MemberListPageDto> {
  const response = await fetcher("/api/members");

  if (!response.ok) {
    throw new Error(`/api/members failed: ${response.status}`);
  }

  return (await response.json()) as MemberListPageDto;
}

export async function loadMemberDetail(memberSlug: string, fetcher: typeof fetch = fetch): Promise<MemberDetailPageDto> {
  const endpoint = `/api/members/${memberSlug}`;
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`${endpoint} failed: ${response.status}`);
  }

  return (await response.json()) as MemberDetailPageDto;
}
