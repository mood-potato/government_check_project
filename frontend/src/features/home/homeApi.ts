import type { HomePageDto } from "./types";

export async function loadHomePage(fetcher: typeof fetch = fetch): Promise<HomePageDto> {
  const response = await fetcher("/api/home");

  if (!response.ok) {
    throw new Error(`/api/home failed: ${response.status}`);
  }

  return (await response.json()) as HomePageDto;
}
