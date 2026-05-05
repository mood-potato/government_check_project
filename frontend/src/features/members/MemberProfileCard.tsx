import type { MemberRefDto } from "./types";

type MemberAvatarProps = {
  member: MemberRefDto;
  className?: string;
};

type MemberProfileCardProps = {
  member: MemberRefDto;
  summary: string;
};

export function formatMemberLine(member: MemberRefDto) {
  return [member.party_name, member.district_name].filter(Boolean).join(" · ");
}

export function MemberAvatar({ member, className = "member-avatar" }: MemberAvatarProps) {
  if (member.profile_image_url) {
    return <img className={className} src={member.profile_image_url} alt={`${member.name} 프로필`} />;
  }

  return (
    <div className={`${className} member-avatar-fallback avatar-fallback`} aria-hidden="true">
      {member.name.slice(0, 1)}
    </div>
  );
}

export function MemberProfileCard({ member, summary }: MemberProfileCardProps) {
  return (
    <a className="member-profile-card" href={`/members/${member.slug}`}>
      <MemberAvatar member={member} className="member-profile-card-photo" />
      <div className="member-profile-card-copy">
        <h3>{member.name}</h3>
        <p>{formatMemberLine(member)}</p>
        <span>{summary}</span>
      </div>
    </a>
  );
}
