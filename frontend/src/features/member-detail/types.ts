export type MemberRefDto = {
  id: string;
  slug: string;
  name: string;
  party_name: string | null;
  district_name: string | null;
  profile_image_url: string | null;
};

export type MemberProfileDto = MemberRefDto & {
  generation_label: string;
  committee_name: string | null;
  status_label: string;
  fact_summary: string;
};

export type MemberMetricDto = {
  label: string;
  value: string;
  supporting_text?: string;
  tone?: "primary" | "tertiary" | "default";
};

export type ConflictRecordDto = {
  id: string;
  topic_label: string;
  date: string;
  meeting_name: string;
  opponent_name: string;
  opponent_detail: string | null;
  quote: string;
};

export type ContradictorySpeechDto = {
  label: string;
  speech_text: string;
  source: string;
  tone: "past" | "recent";
};

export type AgendaRecordDto = {
  id: string;
  title: string;
  meeting_count: number;
  recent_date: string;
  summary: string;
};

export type MemberRelationDto = {
  member: MemberRefDto;
  basis: string;
  value_label: string;
};

export type MemberDetailPageDto = {
  member: MemberProfileDto;
  metrics: MemberMetricDto[];
  conflicts: ConflictRecordDto[];
  contradictory_speeches: [ContradictorySpeechDto, ContradictorySpeechDto];
  agendas: AgendaRecordDto[];
  similar_members: MemberRelationDto[];
  opposing_members: MemberRelationDto[];
  disclaimer: string;
};
