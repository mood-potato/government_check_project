type ApiFetcher = (request: Request) => Promise<Response>;

export function buildApiTargetUrl(requestUrl: string, backendBaseUrl: string) {
  const incomingUrl = new URL(requestUrl);
  const backendUrl = new URL(backendBaseUrl);
  backendUrl.pathname = incomingUrl.pathname;
  backendUrl.search = incomingUrl.search;
  return backendUrl.toString();
}

export async function proxyApiRequest(request: Request, backendBaseUrl: string, fetcher: ApiFetcher = fetch) {
  const targetUrl = buildApiTargetUrl(request.url, backendBaseUrl);
  const headers = new Headers(request.headers);
  headers.delete("host");

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual"
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }

  try {
    return await fetcher(new Request(targetUrl, init));
  } catch {
    return Response.json({ detail: "Backend API unavailable" }, { status: 502 });
  }
}
