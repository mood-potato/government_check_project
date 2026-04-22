export type MemberSpeechDto = {
  spoken_date: string;
  meeting_name: string;
  speech_text: string;
  original_url: string | null;
};

export type HomeMemberRefDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};

export type HomeHeroDto = {
  member: HomeMemberRefDto;
  topic_label: string;
  topic_slug: string | null;
  past_speech: MemberSpeechDto;
  recent_speech: MemberSpeechDto;
  summary: string;
};

export type PopularKeywordDto = {
  label: string;
  slug: string;
};

export type RecentCaseDto = {
  id: string;
  member: HomeMemberRefDto;
  topic_label: string;
  summary: string;
};

export type FeaturedMemberDto = {
  rank: number;
  member: HomeMemberRefDto;
  summary: string;
};

export type HomePageDto = {
  hero: HomeHeroDto | null;
  popular_keywords: PopularKeywordDto[];
  recent_cases: RecentCaseDto[];
  featured_members: FeaturedMemberDto[];
  disclaimer: string;
};
