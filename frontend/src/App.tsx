import { useEffect, useState } from "react";

import { HomePage } from "./features/home/HomePage";
import { loadHomePage } from "./features/home/homeApi";
import type { HomePageDto } from "./features/home/types";
import { MemberDetailPage } from "./features/member-detail/MemberDetailPage";
import { sampleMemberDetailPage } from "./features/member-detail/sampleMemberDetailPage";

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
  if (path.startsWith("/members/")) {
    return <MemberDetailPage data={sampleMemberDetailPage} />;
  }

  return <HomeRoute />;
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
    return <HomeStatus message="의원 데이터를 불러오지 못했습니다." detail={error} />;
  }

  if (!data) {
    return <HomeStatus message="의원 데이터를 불러오는 중입니다." />;
  }

  return <HomePage data={data} />;
}

function HomeStatus({ message, detail }: { message: string; detail?: string }) {
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
