export type MemberRefDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};

export type MemberProfileItemDto = {
  member: MemberRefDto;
  summary: string;
};

export type MemberListPageDto = {
  items: MemberProfileItemDto[];
  disclaimer: string;
};
