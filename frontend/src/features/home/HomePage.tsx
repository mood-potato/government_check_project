import type { HomeHeroDto, HomeMemberRefDto, HomePageDto } from "./types";
import { formatMemberLine, MemberAvatar } from "../members/MemberProfileCard";

type HomePageProps = {
  data: HomePageDto;
  sectionStatus?: {
    hero?: "loading" | "ready" | "error";
    recentCases?: "loading" | "ready" | "error";
    featuredMembers?: "loading" | "ready" | "error";
  };
};

function formatExcerptDate(date: string) {
  return `${date.replaceAll("-", ".")} 발췌`;
}

function memberLine(member: HomeMemberRefDto) {
  return formatMemberLine(member);
}

function HeroCard({ hero }: { hero: HomeHeroDto }) {
  const topicHref = hero.topic_slug ? `/topics/${hero.topic_slug}` : "#";

  return (
    <section className="hero-card" aria-label="최근 포착된 상반 발언 후보">
      <a className="hero-portrait" href={`/members/${hero.member.slug}`} aria-label={`${hero.member.name} 상세 보기`}>
        {hero.member.profile_image_url ? (
          <img src={hero.member.profile_image_url} alt={`${hero.member.name} 초상`} />
        ) : (
          <div className="hero-portrait-fallback">{hero.member.name.slice(0, 1)}</div>
        )}
        <div className="hero-portrait-overlay">
          <h2>{hero.member.name}</h2>
          <p>{memberLine(hero.member)}</p>
        </div>
      </a>

      <div className="hero-analysis">
        <div>
          <div className="tag-row" aria-label="분석 태그">
            <span className="tag tag-blue">최근 업데이트</span>
            <span className="tag tag-soft">자동 분석</span>
            <span className="tag tag-brand">{hero.topic_label}</span>
          </div>

          <div className="timeline-comparison" aria-label="발언 비교">
            <div>
              <span>{formatExcerptDate(hero.past_speech.spoken_date)}</span>
              <p>"{hero.past_speech.speech_text}"</p>
            </div>
            <span className="material-symbols-outlined compare-icon" aria-hidden="true">
              trending_flat
            </span>
            <div>
              <span>{formatExcerptDate(hero.recent_speech.spoken_date)}</span>
              <p>"{hero.recent_speech.speech_text}"</p>
            </div>
          </div>

          <p className="analysis-summary">"{hero.summary}"</p>
        </div>

        <div className="action-row">
          <a className="button button-primary" href={hero.recent_speech.original_url ?? "#"}>
            원문 보기
          </a>
          <a className="button button-soft" href={`/members/${hero.member.slug}`}>
            이 사람 더 보기
          </a>
          <a className="button button-soft" href={topicHref}>
            이 주제 더 보기
          </a>
        </div>
      </div>
    </section>
  );
}

function EmptyHeroCard() {
  return (
    <section className="hero-card empty-card" aria-label="최근 포착된 상반 발언 후보">
      <div>
        <p className="eyebrow">DEMOCRACY IS YOUR VOICE HEARD</p>
        <h2>아직 표시할 상반 발언 후보가 없습니다.</h2>
        <p>새 분석 결과가 준비되면 가장 최근 사례를 이곳에 보여줍니다.</p>
      </div>
    </section>
  );
}

function HeroLoadingCard() {
  return (
    <section className="hero-card empty-card" aria-label="최근 포착된 상반 발언 후보">
      <div>
        <p className="eyebrow">자동 분석 불러오는 중</p>
        <h2>최근 상반 발언 후보를 확인하고 있습니다.</h2>
        <p>첫 화면에 보여줄 사례만 먼저 불러옵니다.</p>
      </div>
    </section>
  );
}

function SectionStatus({ message }: { message: string }) {
  return (
    <div className="home-status" role="status">
      <p>{message}</p>
    </div>
  );
}

export function HomePage({ data, sectionStatus = {} }: HomePageProps) {
  const heroStatus = sectionStatus.hero ?? "ready";
  const recentCasesStatus = sectionStatus.recentCases ?? "ready";
  const featuredMembersStatus = sectionStatus.featuredMembers ?? "ready";

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
        <header className="page-hero">
          <p className="eyebrow">DEMOCRACY IS YOUR VOICE HEARD</p>
          <h1>
            최근 포착된 <span>상반 발언</span> 후보
          </h1>
          <p className="hero-lede">
            투표 전에, 지금 비교해보세요. AssemblyVoice가 인공지능으로 공직자의 발언 일관성을 투명하게
            분석합니다.
          </p>
          <form className="hero-search" action="/search" role="search">
            <span className="material-symbols-outlined" aria-hidden="true">
              search
            </span>
            <input name="q" type="search" placeholder="의원 이름이나 쟁점으로 검색" aria-label="의원 이름이나 쟁점으로 검색" />
          </form>
        </header>

        {heroStatus === "loading" ? <HeroLoadingCard /> : data.hero ? <HeroCard hero={data.hero} /> : <EmptyHeroCard />}

        {data.recent_cases.length > 0 ? (
          <section className="content-section">
            <h3 className="section-title">
              <span className="material-symbols-outlined" aria-hidden="true">
                analytics
              </span>
              추가 분석 사례
            </h3>
            <div className="case-grid">
              {data.recent_cases.map((item) => (
                <a className="case-card" href={`/members/${item.member.slug}`} key={item.id}>
                  <div className="case-member">
                    <MemberAvatar member={item.member} className="avatar" />
                    <div>
                      <h4>{item.member.name}</h4>
                      <p>{item.topic_label}</p>
                    </div>
                  </div>
                  <p>{item.summary}</p>
                </a>
              ))}
            </div>
          </section>
        ) : recentCasesStatus === "loading" ? (
          <SectionStatus message="추가 분석 사례를 불러오는 중입니다." />
        ) : null}

        {data.featured_members.length > 0 ? (
          <section className="content-section">
            <h3 className="section-title">최근 발언한 인물</h3>
            <div className="featured-list">
              {data.featured_members.map((item) => (
                <a className="featured-row" href={`/members/${item.member.slug}`} key={item.member.id}>
                  <span className="rank">{String(item.rank).padStart(2, "0")}</span>
                  <MemberAvatar member={item.member} className="avatar avatar-sm" />
                  <div>
                    <h4>{item.member.name}</h4>
                    <p>{item.summary}</p>
                  </div>
                  <span className="material-symbols-outlined chevron" aria-hidden="true">
                    chevron_right
                  </span>
                </a>
              ))}
            </div>
          </section>
        ) : featuredMembersStatus === "loading" ? (
          <SectionStatus message="최근 발언한 인물을 불러오는 중입니다." />
        ) : null}

        <aside className="notice">
          <span className="material-symbols-outlined" aria-hidden="true">
            info
          </span>
          <p>{data.disclaimer}</p>
        </aside>
      </main>

      <footer className="footer">
        <div>
          <strong>AssemblyVoice</strong>
          <p>© 2026 AssemblyVoice. Bridging the gap between citizens and assembly.</p>
        </div>
        <div className="footer-links">
          <a href="/privacy">Privacy Policy</a>
          <a href="/terms">Terms of Service</a>
          <a href="/accessibility">Accessibility</a>
          <a href="/contact">Contact Us</a>
        </div>
      </footer>
    </div>
  );
}
