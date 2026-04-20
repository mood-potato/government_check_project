import { expect, test } from "bun:test";

const styles = await Bun.file(new URL("./styles.css", import.meta.url)).text();
test("keeps cards and controls within the app radius scale", () => {
  expect(styles).not.toContain("border-radius: 1rem");
  expect(styles).not.toContain("border-radius: 1.5rem");
  expect(styles).not.toContain("border-radius: 2rem");
  expect(styles).not.toContain("border-radius: 3rem");
  expect(styles).not.toContain("border-radius: 9999px");
});

test("does not rely on negative letter spacing", () => {
  expect(styles).not.toMatch(/letter-spacing:\s*-/);
});

test("keeps the fixed header translucent like the source home page", () => {
  const topNavStyles = styles.match(/\.top-nav\s*\{[^}]*\}/)?.[0] ?? "";

  expect(topNavStyles).toContain("position: fixed");
  expect(topNavStyles).toContain("backdrop-filter");
});
