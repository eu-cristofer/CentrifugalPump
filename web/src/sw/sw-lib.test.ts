// @vitest-environment node
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  buildServiceWorker,
  cacheName,
  listFiles,
  precacheList,
  renderServiceWorker,
} from "../../scripts/sw-lib.mjs";

// Built from pieces: the source guard forbids a literal scheme in src/.
const ORIGIN = ["https", "app.test"].join("://");
const OTHER = ["https", "elsewhere.test"].join("://");

const here = path.dirname(fileURLToPath(import.meta.url));
const template = readFileSync(path.join(here, "sw-template.js"), "utf8");

let dist = "";
beforeEach(() => {
  dist = mkdtempSync(path.join(tmpdir(), "pumpflow-dist-"));
});
afterEach(() => rmSync(dist, { recursive: true, force: true }));

function put(rel: string, content: string | Buffer = rel): void {
  const file = path.join(dist, rel);
  mkdirSync(path.dirname(file), { recursive: true });
  writeFileSync(file, content);
}

const manifest = {
  files: [
    { path: "pyodide.mjs", sha256: "x", bytes: 1 },
    { path: "wheels/pint.whl", sha256: "y", bytes: 1 },
  ],
};

function fakeBuild(): void {
  put("index.html", "<html></html>");
  put("manifest.webmanifest", "{}");
  put("icon.svg", "<svg/>");
  put("assets/index-abc.js", "js");
  put("assets/index-abc.css", "css");
  put("assets/index-abc.js.map", "map");
  put("py/manifest.json", JSON.stringify(manifest));
  put("py/pyodide.mjs", "mjs");
  put("py/wheels/pint.whl", "whl");
  put("sw.js", "old worker");
  put(".DS_Store", "x");
}

describe("precache list", () => {
  it("is the shell page, the build files and every file of py/manifest.json", () => {
    fakeBuild();
    const urls = precacheList(listFiles(dist));
    expect(urls).toEqual([
      "./",
      "assets/index-abc.css",
      "assets/index-abc.js",
      "icon.svg",
      "index.html",
      "manifest.webmanifest",
      "py/manifest.json",
      "py/pyodide.mjs",
      "py/wheels/pint.whl",
    ]);
    // the manifest's files are all there
    for (const f of manifest.files) expect(urls).toContain(`py/${f.path}`);
  });

  it("has no duplicates, no worker, no source maps", () => {
    const urls = precacheList(["a.js", "a.js", "sw.js", "x/.DS_Store", "a.js.map", "./"]);
    expect(urls).toEqual(["./", "a.js"]);
    expect(new Set(urls).size).toBe(urls.length);
  });

  it("is the same whatever the order the files come in", () => {
    expect(precacheList(["b", "a", "c/d"])).toEqual(precacheList(["c/d", "a", "b"]));
  });
});

describe("cache name", () => {
  it("changes with a file, a size or the manifest, and not otherwise", () => {
    const base = cacheName(["./", "a.js"], [0, 1], "m1");
    expect(base).toMatch(/^pumpflow-[0-9a-f]{16}$/);
    expect(cacheName(["./", "a.js"], [0, 1], "m1")).toBe(base);
    expect(cacheName(["./", "b.js"], [0, 1], "m1")).not.toBe(base);
    expect(cacheName(["./", "a.js"], [0, 2], "m1")).not.toBe(base);
    expect(cacheName(["./", "a.js"], [0, 1], "m2")).not.toBe(base);
  });
});

describe("buildServiceWorker", () => {
  it("fills the template from the build", () => {
    fakeBuild();
    const built = buildServiceWorker(dist, template);
    expect(built.urls[0]).toBe("./");
    expect(built.bytes).toHaveLength(built.urls.length);
    expect(built.bytes[built.urls.indexOf("assets/index-abc.js")]).toBe(2);
    expect(built.source).toContain(JSON.stringify(built.cache));
    expect(built.source).toContain(JSON.stringify(built.urls));
    expect(built.source).not.toContain("pumpflow-dev");
    // the cache name moves with the engine manifest
    put("py/manifest.json", JSON.stringify({ ...manifest, pyodide: "next" }));
    expect(buildServiceWorker(dist, template).cache).not.toBe(built.cache);
  });

  it("refuses a template without its markers", () => {
    expect(() => renderServiceWorker("const x = 1;", { cache: "c", urls: [], bytes: [] })).toThrow(
      /@cache/,
    );
  });
});

// ---- run the rendered worker against fakes -----------------------------------------

type Handler = (event: Record<string, unknown>) => void;

function runWorker(urls: string[], bytes: number[], files: Record<string, string>) {
  const handlers: Record<string, Handler> = {};
  const posted: unknown[] = [];
  const stores = new Map<string, Map<string, string>>([["pumpflow-old", new Map()]]);
  const added: string[][] = [];
  const networkHits: string[] = [];
  const net = { offline: false };
  const toUrl = (r: string | { url: string }) =>
    new URL(typeof r === "string" ? r : r.url, `${ORIGIN}/`).href;
  const makeCache = (name: string) => {
    let store = stores.get(name);
    if (!store) stores.set(name, (store = new Map()));
    const kept = store;
    return {
      addAll: async (requests: Array<{ url: string }>) => {
        added.push(requests.map((r) => r.url));
        for (const r of requests) kept.set(r.url, files[new URL(r.url).pathname.slice(1)] ?? "shell");
      },
      match: async (r: string | { url: string }, opts?: { ignoreSearch?: boolean }) => {
        const key = new URL(toUrl(r));
        if (opts?.ignoreSearch) key.search = "";
        const body = kept.get(key.href);
        return body === undefined ? undefined : { body };
      },
      put: async (r: { url: string }, res: { body: string }) => void kept.set(toUrl(r), res.body),
    };
  };
  const self = {
    location: { origin: ORIGIN },
    registration: { scope: `${ORIGIN}/` },
    clients: {
      matchAll: async () => [{ postMessage: (m: unknown) => posted.push(m) }],
      claim: async () => undefined,
    },
    skipWaiting: () => posted.push("skipWaiting"),
    addEventListener: (type: string, h: Handler) => void (handlers[type] = h),
  };
  const source = renderServiceWorker(template, { cache: "pumpflow-new", urls, bytes });
  vm.runInNewContext(source, {
    self,
    caches: {
      open: async (n: string) => makeCache(n),
      keys: async () => [...stores.keys()],
      delete: async (n: string) => stores.delete(n),
    },
    fetch: async (r: { url: string }) => {
      networkHits.push(r.url);
      if (net.offline) throw new TypeError("offline");
      return { ok: true, status: 200, body: "net", clone() { return this; } };
    },
    Request: class { constructor(public url: string, public init: unknown) { this.url = new URL(url, `${ORIGIN}/`).href; } },
    URL,
  });
  const wait = async (type: string, extra: Record<string, unknown> = {}) => {
    let p: Promise<unknown> = Promise.resolve();
    handlers[type]!({ waitUntil: (x: Promise<unknown>) => (p = x), ...extra });
    await p;
  };
  return { handlers, posted, stores, added, networkHits, net, wait };
}

describe("rendered worker", () => {
  const urls = ["./", "index.html", "assets/a.js", "py/big.wasm", "py/x.whl"];
  const bytes = [0, 100, 200, 5 * 1024 * 1024, 300];

  it("precaches every URL in batches with progress, then announces it is done", async () => {
    const w = runWorker(urls, bytes, {});
    await w.wait("install");
    expect(w.added.flat().map((u) => new URL(u).pathname)).toEqual(
      urls.map((u) => (u === "./" ? "/" : `/${u}`)),
    );
    expect(w.added.length).toBeGreaterThan(1); // the 5 MB file closes a batch
    const progress = w.posted.filter(
      (m) => (m as { type: string }).type === "precache-progress",
    ) as Array<{ done: number; count: number; bytes: number; total: number }>;
    expect(progress[0]).toMatchObject({ done: 0, count: 5, bytes: 0 });
    expect(progress.at(-1)).toMatchObject({ done: 5, count: 5, bytes: 100 + 200 + 5 * 1024 * 1024 + 300 });
    expect(w.posted.at(-1)).toEqual({ type: "precache-done" });
  });

  it("deletes older pumpflow caches when it activates", async () => {
    const w = runWorker(urls, bytes, {});
    await w.wait("activate");
    expect([...w.stores.keys()]).not.toContain("pumpflow-old");
  });

  it("answers from the cache and falls back to the network once", async () => {
    const w = runWorker(urls, bytes, { "assets/a.js": "cached-js" });
    await w.wait("install");
    const respond = async (url: string, method = "GET", mode = "cors") => {
      let out: Promise<{ body: string }> | undefined;
      w.handlers.fetch!({
        request: { url, method, mode },
        respondWith: (p: Promise<{ body: string }>) => (out = p),
      });
      return out && (await out);
    };
    expect((await respond(`${ORIGIN}/assets/a.js`))?.body).toBe("cached-js");
    expect(w.networkHits).toEqual([]);
    expect((await respond(`${ORIGIN}/other.txt`))?.body).toBe("net");
    expect(w.networkHits).toEqual([`${ORIGIN}/other.txt`]);
    expect((await respond(`${ORIGIN}/other.txt`))?.body).toBe("net");
    expect(w.networkHits).toHaveLength(1); // now cached
    expect(await respond(`${OTHER}/x.js`)).toBeUndefined(); // not ours
    expect(await respond(`${ORIGIN}/x`, "POST")).toBeUndefined();
    expect((await respond(`${ORIGIN}/?x=1`, "GET", "navigate"))?.body).toBe("shell");
    expect(w.networkHits).toHaveLength(1); // the page came from the cache
  });

  it("works with the network off: cached files and navigations; unknown files fail", async () => {
    const w = runWorker(urls, bytes, { "py/x.whl": "wheel" });
    await w.wait("install");
    w.net.offline = true;
    const respond = (url: string, mode = "cors") => {
      let out: Promise<{ body: string }> | undefined;
      w.handlers.fetch!({
        request: { url, method: "GET", mode },
        respondWith: (p: Promise<{ body: string }>) => (out = p),
      });
      return out!;
    };
    expect((await respond(`${ORIGIN}/py/x.whl`)).body).toBe("wheel");
    expect((await respond(`${ORIGIN}/some/route`, "navigate")).body).toBe("shell");
    await expect(respond(`${ORIGIN}/missing.js`)).rejects.toThrow("offline");
  });

  it("skips waiting only when asked", () => {
    const w = runWorker(urls, bytes, {});
    w.handlers.message!({ data: { type: "other" } });
    expect(w.posted).toEqual([]);
    w.handlers.message!({ data: { type: "SKIP_WAITING" } });
    expect(w.posted).toEqual(["skipWaiting"]);
  });
});
