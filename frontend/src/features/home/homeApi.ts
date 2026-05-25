import type { FeaturedMemberDto, HomeHeroDto, HomePageDto, RecentCaseDto } from "./types";

export async function loadHomePage(fetcher: typeof fetch = fetch): Promise<HomePageDto> {
  return fetchJson<HomePageDto>("/api/home", fetcher);
}

export async function loadHomeHero(fetcher: typeof fetch = fetch): Promise<HomeHeroDto | null> {
  return fetchJson<HomeHeroDto | null>("/api/home/hero", fetcher);
}

export async function loadRecentCases(fetcher: typeof fetch = fetch): Promise<RecentCaseDto[]> {
  return fetchJson<RecentCaseDto[]>("/api/home/recent-cases", fetcher);
}

export async function loadFeaturedMembers(fetcher: typeof fetch = fetch): Promise<FeaturedMemberDto[]> {
  return fetchJson<FeaturedMemberDto[]>("/api/home/featured-members", fetcher);
}

async function fetchJson<T>(endpoint: string, fetcher: typeof fetch): Promise<T> {
  const response = await fetcher(endpoint);

  if (!response.ok) {
    throw new Error(`${endpoint} failed: ${response.status}`);
  }

  return (await response.json()) as T;
}
