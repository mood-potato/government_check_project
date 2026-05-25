import { useEffect, useState } from "react";

import { HomePage } from "./features/home/HomePage";
import { loadFeaturedMembers, loadHomeHero, loadRecentCases } from "./features/home/homeApi";
import type { HomePageDto } from "./features/home/types";
import { MemberDetailPage } from "./features/member-detail/MemberDetailPage";
import type { MemberDetailPageDto } from "./features/member-detail/types";
import { MemberListPage } from "./features/members/MemberListPage";
import { loadMemberDetail, loadMembers } from "./features/members/memberApi";
import type { MemberListPageDto } from "./features/members/types";

type AppProps = {
  path?: string;
};

function currentPath() {
  if (typeof window === "undefined") {
    return "/";
  }

  return window.location.pathname;
}

export function App({ path = currentPath() }: AppProps) {
  if (path === "/members") {
    return <MemberListRoute />;
  }

  if (path.startsWith("/members/")) {
    return <MemberDetailRoute slug={path.replace("/members/", "")} />;
  }

  return <HomeRoute />;
}

function MemberListRoute() {
  const [data, setData] = useState<MemberListPageDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    loadMembers()
      .then((memberData) => {
        if (isActive) {
          setData(memberData);
        }
      })
      .catch((err: unknown) => {
        if (isActive) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  if (error) {
    return <AppStatus message="국회의원 프로필을 불러오지 못했습니다." detail={error} />;
  }

  if (!data) {
    return <AppStatus message="국회의원 프로필을 불러오는 중입니다." />;
  }

  return <MemberListPage data={data} />;
}

function MemberDetailRoute({ slug }: { slug: string }) {
  const [data, setData] = useState<MemberDetailPageDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    loadMemberDetail(slug)
      .then((memberData) => {
        if (isActive) {
          setData(memberData);
        }
      })
      .catch((err: unknown) => {
        if (isActive) {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      });

    return () => {
      isActive = false;
    };
  }, [slug]);

  if (error) {
    return <AppStatus message="의원 정보를 불러오지 못했습니다." detail={error} />;
  }

  if (!data) {
    return <AppStatus message="의원 정보를 불러오는 중입니다." />;
  }

  return <MemberDetailPage data={data} />;
}

function HomeRoute() {
  const [data, setData] = useState<HomePageDto>({
    hero: null,
    popular_keywords: [],
    recent_cases: [],
    featured_members: [],
    disclaimer: "자동 분석으로 비교된 발언입니다. 원문 맥락을 함께 확인하세요."
  });
  const [heroStatus, setHeroStatus] = useState<"loading" | "ready" | "error">("loading");
  const [recentCasesStatus, setRecentCasesStatus] = useState<"loading" | "ready" | "error">("loading");
  const [featuredMembersStatus, setFeaturedMembersStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let isActive = true;

    loadHomeHero()
      .then((hero) => {
        if (isActive) {
          setData((current) => ({ ...current, hero }));
          setHeroStatus("ready");
        }
      })
      .catch(() => {
        if (isActive) {
          setHeroStatus("error");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    loadRecentCases()
      .then((recentCases) => {
        if (isActive) {
          setData((current) => ({ ...current, recent_cases: recentCases }));
          setRecentCasesStatus("ready");
        }
      })
      .catch(() => {
        if (isActive) {
          setRecentCasesStatus("error");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    let isActive = true;

    loadFeaturedMembers()
      .then((featuredMembers) => {
        if (isActive) {
          setData((current) => ({ ...current, featured_members: featuredMembers }));
          setFeaturedMembersStatus("ready");
        }
      })
      .catch(() => {
        if (isActive) {
          setFeaturedMembersStatus("error");
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  return (
    <HomePage
      data={data}
      sectionStatus={{
        hero: heroStatus,
        recentCases: recentCasesStatus,
        featuredMembers: featuredMembersStatus
      }}
    />
  );
}

function AppStatus({ message, detail }: { message: string; detail?: string }) {
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
        <section className="home-status" role="status">
          <p>{message}</p>
          {detail ? <span>{detail}</span> : null}
        </section>
      </main>
    </div>
  );
}
