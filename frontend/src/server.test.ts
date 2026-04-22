import { expect, test } from "bun:test";

const serverSource = await Bun.file(new URL("./server.ts", import.meta.url)).text();

test("allows the dev server port to be configured", () => {
  expect(serverSource).toContain("process.env.PORT");
  expect(serverSource).toContain("port:");
});
