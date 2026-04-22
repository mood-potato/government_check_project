import { HomePage } from "./features/home/HomePage";
import { sampleHomePage } from "./features/home/sampleHomePage";
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

  return <HomePage data={sampleHomePage} />;
}
