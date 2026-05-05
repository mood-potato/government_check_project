import { expect, test } from "bun:test";

import { buildApiTargetUrl, proxyApiRequest } from "./serverProxy";

const serverSource = await Bun.file(new URL("./server.ts", import.meta.url)).text();

test("allows the dev server port to be configured", () => {
  expect(serverSource).toContain("process.env.PORT");
  expect(serverSource).toContain("port:");
});

test("proxies API routes before falling back to the React app", () => {
  expect(serverSource).toContain('"/api/*"');
  expect(serverSource.indexOf('"/api/*"')).toBeLessThan(serverSource.indexOf('"/*"'));
  expect(serverSource).toContain("process.env.BACKEND_URL");
});

test("builds backend API URLs with the original path and query", () => {
  const targetUrl = buildApiTargetUrl("http://localhost:3000/api/members?limit=20", "http://localhost:8000");

  expect(targetUrl).toBe("http://localhost:8000/api/members?limit=20");
});

test("forwards API requests to the configured backend", async () => {
  const calls: Request[] = [];
  const request = new Request("http://localhost:3000/api/search", {
    method: "POST",
    body: JSON.stringify({ query: "테스트" }),
    headers: { "content-type": "application/json" }
  });
  const fetcher = async (input: Request) => {
    calls.push(input);
    return Response.json({ ok: true });
  };

  const response = await proxyApiRequest(request, "http://localhost:8000", fetcher);

  expect(response.status).toBe(200);
  expect(calls[0].url).toBe("http://localhost:8000/api/search");
  expect(calls[0].method).toBe("POST");
  expect(calls[0].headers.get("content-type")).toBe("application/json");
});

test("returns JSON when the backend API is unavailable", async () => {
  const response = await proxyApiRequest(new Request("http://localhost:3000/api/home"), "http://localhost:8000", async () => {
    throw new Error("connection refused");
  });

  expect(response.status).toBe(502);
  expect(response.headers.get("content-type")).toContain("application/json");
  await expect(response.json()).resolves.toEqual({ detail: "Backend API unavailable" });
});
