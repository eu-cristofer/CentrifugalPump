// Post-build: writes dist/sw.js (the offline service worker) from src/sw/sw-template.js.
// Build time only.  Usage: node scripts/sw.mjs   (npm run build runs it after vite build)
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SW_FILE, buildServiceWorker } from "./sw-lib.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const dist = path.join(webRoot, "dist");
if (!existsSync(path.join(dist, "index.html"))) throw new Error("dist/ is empty: run vite build first");

const template = readFileSync(path.join(webRoot, "src", "sw", "sw-template.js"), "utf8");
const { cache, urls, bytes, source } = buildServiceWorker(dist, template);
writeFileSync(path.join(dist, SW_FILE), source);
const mb = bytes.reduce((a, b) => a + b, 0) / 1024 ** 2;
console.log(`${SW_FILE}: ${cache}, ${urls.length} files, ${mb.toFixed(1)} MB`);
