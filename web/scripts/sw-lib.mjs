// Pure helpers of the service-worker build (scripts/sw.mjs) so they can be tested.
// Build time only.
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

/** The generated worker; never part of its own precache list. */
export const SW_FILE = "sw.js";
export const CACHE_PREFIX = "pumpflow-";

const IGNORED = new Set([SW_FILE, ".DS_Store"]);

const sha256 = (data) => createHash("sha256").update(data).digest("hex");

/** Every file under `dir` as a sorted, "/"-separated path relative to `dir`. */
export function listFiles(dir) {
  const out = [];
  const walk = (sub) => {
    for (const entry of readdirSync(path.join(dir, sub), { withFileTypes: true })) {
      const rel = sub ? `${sub}/${entry.name}` : entry.name;
      const isDir = entry.isDirectory() || (entry.isSymbolicLink() && statSync(path.join(dir, rel)).isDirectory());
      if (isDir) walk(rel);
      else out.push(rel);
    }
  };
  walk("");
  return out.sort();
}

/**
 * URLs to precache: "./" (the shell page) and every build file, sorted, without
 * duplicates, the worker itself, source maps and OS litter.
 */
export function precacheList(files) {
  const urls = new Set(["./"]);
  for (const f of files) {
    const name = f.split("/").pop();
    if (IGNORED.has(f) || IGNORED.has(name) || f.endsWith(".map")) continue;
    urls.add(f);
  }
  return [...urls].sort();
}

/** Cache name: pumpflow- + a hash of the sorted URL list, their sizes and py/manifest.json. */
export function cacheName(urls, sizes, manifestSha) {
  const body = urls.map((u, i) => `${u}:${sizes[i] ?? 0}`).join("\n");
  return CACHE_PREFIX + sha256(`${body}\n${manifestSha}`).slice(0, 16);
}

const MARKERS = { cache: /\/\* @cache \*\/ [^;]*;/, precache: /\/\* @precache \*\/ [^;]*;/, bytes: /\/\* @bytes \*\/ [^;]*;/ };

/** Fill the three marked constants of the worker template. */
export function renderServiceWorker(template, { cache, urls, bytes }) {
  const values = { cache, precache: urls, bytes };
  let out = template;
  for (const [key, re] of Object.entries(MARKERS)) {
    if (!re.test(out)) throw new Error(`service worker template has no @${key} marker`);
    out = out.replace(re, () => `${JSON.stringify(values[key])};`);
  }
  return out;
}

/** Read the build in `distDir` and return the worker source with its cache name and lists. */
export function buildServiceWorker(distDir, templateSource) {
  const urls = precacheList(listFiles(distDir));
  const sizes = urls.map((u) => (u === "./" ? 0 : statSync(path.join(distDir, u)).size));
  const manifestPath = path.join(distDir, "py", "manifest.json");
  const manifestSha = existsSync(manifestPath) ? sha256(readFileSync(manifestPath)) : "";
  const cache = cacheName(urls, sizes, manifestSha);
  return { cache, urls, bytes: sizes, source: renderServiceWorker(templateSource, { cache, urls, bytes: sizes }) };
}
