import type {
  AgendaRecordDto,
  ConflictRecordDto,
  MemberDetailPageDto,
  MemberMetricDto,
  MemberRelationDto
} from "./types";
import { formatMemberLine, MemberAvatar } from "../members/MemberProfileCard";

type MemberDetailPageProps = {
  data: MemberDetailPageDto;
};

function DetailNav() {
  return (
    <nav className="top-nav">
      <div className="nav-inner">
        <a className="brand" href="/">
          AssemblyVoice
        </a>
      </div>
    </nav>
  );
}

function MetricCard({ metric }: { metric: MemberMetricDto }) {
  return (
    <article className={`metric-card ${metric.tone ? `metric-${metric.tone}` : ""}`}>
      <p>{metric.label}</p>
      <div>
        <strong>{metric.value}</strong>
        {metric.supporting_text ? <span>{metric.supporting_text}</span> : null}
      </div>
    </article>
  );
}

function ConflictCard({ conflict }: { conflict: ConflictRecordDto }) {
  const opponent = [conflict.opponent_name, conflict.opponent_detail ? `(${conflict.opponent_detail})` : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <article className="conflict-card">
      <div className="card-meta-row">
        <span className="pill pill-soft">{conflict.topic_label}</span>
        <time>{conflict.date}</time>
      </div>
      <p className="meeting-name">{conflict.meeting_name}</p>
      <div className="opponent-box">
        <div className="mini-avatar" aria-hidden="true" />
        <div>
          <span>Conflict with</span>
          <strong>{opponent}</strong>
        </div>
      </div>
      <blockquote>{conflict.quote}</blockquote>
    </article>
  );
}

function AgendaRow({ agenda }: { agenda: AgendaRecordDto }) {
  return (
    <a className="agenda-row" href={`/agendas/${agenda.id}`}>
      <div>
        <h3>{agenda.title}</h3>
        <p>
          <span>참여 회의 {agenda.meeting_count}회</span>
          <span>최근 언급: {agenda.recent_date}</span>
        </p>
      </div>
      <p className="agenda-summary">{agenda.summary}</p>
      <span className="material-symbols-outlined" aria-hidden="true">
        arrow_forward_ios
      </span>
    </a>
  );
}

function RelationList({
  title,
  icon,
  variant,
  relations
}: {
  title: string;
  icon: string;
  variant: "similar" | "opposing";
  relations: MemberRelationDto[];
}) {
  return (
    <section>
      <h3 className="relation-title">
        <span className={`material-symbols-outlined relation-icon-${variant}`} aria-hidden="true">
          {icon}
        </span>
        {title}
      </h3>
      <div className="relation-list">
        {relations.map((relation) => (
          <a className={`relation-card relation-${variant}`} href={`/members/${relation.member.slug}`} key={relation.member.id}>
            <MemberAvatar member={relation.member} className="relation-avatar" />
            <div>
              <h4>{relation.member.name}</h4>
              <p>{relation.basis}</p>
            </div>
            <div className="relation-value">
              <strong>{relation.value_label}</strong>
              <span>{variant === "similar" ? "Match" : "Conflicts"}</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

export function MemberDetailPage({ data }: MemberDetailPageProps) {
  const memberLine = [formatMemberLine(data.member), data.member.committee_name].filter(Boolean).join(" · ");

  return (
    <div className="app-shell member-detail-shell">
      <DetailNav />

      <main className="main-content member-detail-main">
        <section className="member-profile-hero">
          <div className="profile-photo-frame">
            <MemberAvatar member={data.member} className="profile-photo" />
          </div>

          <div className="profile-copy">
            <div className="profile-kicker">
              <span className="pill pill-blue">{data.member.status_label}</span>
              <span>{data.member.generation_label}</span>
            </div>
            <h1>{data.member.name}</h1>
            <p className="member-line">{memberLine}</p>
            <p className="fact-summary">"{data.member.fact_summary}"</p>
            <div className="action-row">
              <a className="button button-primary" href="#recent-speeches">
                <span className="material-symbols-outlined" aria-hidden="true">
                  forum
                </span>
                최근 발언 보기
              </a>
              <a className="button button-soft" href="#agendas">
                <span className="material-symbols-outlined" aria-hidden="true">
                  list_alt
                </span>
                참여 안건 보기
              </a>
            </div>
          </div>
        </section>

        <section className="metric-grid" aria-label="주요 요약">
          {data.metrics.map((metric) => (
            <MetricCard metric={metric} key={metric.label} />
          ))}
        </section>

        <section className="member-section">
          <div className="section-heading">
            <h2>이 사람이 자주 선 갈등</h2>
            <p>주요 쟁점별 상충되는 의견을 가졌던 대화 상대와 시점입니다.</p>
          </div>
          <div className="conflict-grid">
            {data.conflicts.map((conflict) => (
              <ConflictCard conflict={conflict} key={conflict.id} />
            ))}
          </div>
        </section>

        <section className="contradiction-panel" id="recent-speeches">
          <div className="contradiction-heading">
            <div>
              <h2>상반 발언 분석</h2>
              <p>동일 의원의 과거와 현재 발언 중 논리적 변화가 감지된 구간입니다.</p>
            </div>
            <div className="analysis-tools">
              <span>
                <span className="material-symbols-outlined" aria-hidden="true">
                  auto_awesome
                </span>
                자동 분석으로 비교된 발언
              </span>
              <a href="#source-context">원문 맥락 확인</a>
            </div>
          </div>
          <div className="speech-compare-grid">
            {data.contradictory_speeches.map((speech) => (
              <article className={`speech-card speech-${speech.tone}`} key={speech.label}>
                <div>
                  <span aria-hidden="true" />
                  <strong>{speech.label}</strong>
                </div>
                <p>"{speech.speech_text}"</p>
                <small>{speech.source}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="member-section" id="agendas">
          <h2 className="standalone-title">참여 안건 기록</h2>
          <div className="agenda-list">
            {data.agendas.map((agenda) => (
              <AgendaRow agenda={agenda} key={agenda.id} />
            ))}
          </div>
        </section>

        <div className="relation-grid">
          <RelationList title="논리가 유사한 의원" icon="handshake" variant="similar" relations={data.similar_members} />
          <RelationList title="주요 갈등 상대" icon="swords" variant="opposing" relations={data.opposing_members} />
        </div>

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
