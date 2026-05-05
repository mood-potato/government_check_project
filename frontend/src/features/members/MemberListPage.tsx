import { MemberProfileCard } from "./MemberProfileCard";
import type { MemberListPageDto } from "./types";

type MemberListPageProps = {
  data: MemberListPageDto;
};

export function MemberListPage({ data }: MemberListPageProps) {
  return (
    <div className="app-shell">
      <nav className="top-nav">
        <div className="nav-inner">
          <a className="brand" href="/">
            AssemblyVoice
          </a>
        </div>
      </nav>

      <main className="main-content">
        <header className="member-list-heading">
          <p className="eyebrow">MEMBER PROFILES</p>
          <h1>국회의원 프로필</h1>
          <p>얼굴, 이름, 정당, 선거구를 기준으로 국회의원 프로필을 빠르게 확인합니다.</p>
        </header>

        <section className="member-profile-grid" aria-label="국회의원 프로필 목록">
          {data.items.map((item) => (
            <MemberProfileCard member={item.member} summary={item.summary} key={item.member.id} />
          ))}
        </section>

        <aside className="notice">
          <span className="material-symbols-outlined" aria-hidden="true">
            info
          </span>
          <p>{data.disclaimer}</p>
        </aside>
      </main>
    </div>
  );
}
