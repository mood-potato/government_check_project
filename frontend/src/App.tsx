import { useEffect, useState } from "react";

import { HomePage } from "./features/home/HomePage";
import { loadHomePage } from "./features/home/homeApi";
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
  const [data, setData] = useState<HomePageDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isActive = true;

    loadHomePage()
      .then((homeData) => {
        if (isActive) {
          setData(homeData);
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
    return <AppStatus message="의원 데이터를 불러오지 못했습니다." detail={error} />;
  }

  if (!data) {
    return <AppStatus message="의원 데이터를 불러오는 중입니다." />;
  }

  return <HomePage data={data} />;
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
