// @vitest-environment node
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";

const webRoot = fileURLToPath(new URL("../", import.meta.url));
const srcDir = path.join(webRoot, "src");

function walk(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );
}

beforeAll(() => {
  execFileSync(process.execPath, [path.join(webRoot, "scripts", "tokens.mjs")], {
    cwd: webRoot,
  });
});

describe("tokens.css", () => {
  it("is generated from the design tokens and defines --accent", () => {
    const css = readFileSync(path.join(srcDir, "tokens.css"), "utf8");
    expect(css).toContain("--accent:");
    expect(css).toContain("--font-sans:");
  });
});

describe("source guards", () => {
  const sources = walk(srcDir).filter(
    (f) =>
      /\.(ts|tsx|css|js)$/.test(f) &&
      path.basename(f) !== "tokens.css" &&
      path.basename(f) !== "guards.test.ts",
  );
  // Built from pieces so this file does not match its own patterns.
  const url = new RegExp("https?" + ":" + "//");
  const hex = new RegExp("#[0-9a-fA-F]{3,8}\\b");

  it("finds source files", () => {
    expect(sources.length).toBeGreaterThan(3);
  });

  it("references no http(s) URL (offline rule)", () => {
    const files = [...sources, path.join(webRoot, "index.html")];
    const offenders = files.filter((f) => url.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });

  it("uses no hex colour literals (design tokens only)", () => {
    const offenders = sources.filter((f) => hex.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });
});
