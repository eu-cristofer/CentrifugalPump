// PumpFlow service worker: caches the app shell and the Python engine so the app
// starts and works with the network off.  scripts/sw.mjs renders this template into
// dist/sw.js, replacing the three marked constants.  Plain JavaScript, no libraries;
// it only requests same-origin files.

const CACHE = /* @cache */ "pumpflow-dev";
/** URLs relative to this file: "./" and every file of the build. */
const PRECACHE = /* @precache */ [];
/** Size in bytes of each PRECACHE entry (same order), for the progress report. */
const BYTES = /* @bytes */ [];

const PREFIX = "pumpflow-";
const BATCH_FILES = 8;
const BATCH_BYTES = 4 * 1024 * 1024;

async function notify(message) {
  const windows = await self.clients.matchAll({ includeUncontrolled: true, type: "window" });
  for (const client of windows) client.postMessage(message);
}

/** The PRECACHE indices in batches of at most BATCH_FILES files or about BATCH_BYTES bytes. */
function batches() {
  const out = [];
  let current = [];
  let size = 0;
  PRECACHE.forEach((_, i) => {
    current.push(i);
    size += BYTES[i] || 0;
    if (current.length >= BATCH_FILES || size >= BATCH_BYTES) {
      out.push(current);
      current = [];
      size = 0;
    }
  });
  if (current.length) out.push(current);
  return out;
}

async function precache() {
  const cache = await caches.open(CACHE);
  const total = BYTES.reduce((a, b) => a + b, 0);
  let bytes = 0;
  let done = 0;
  const report = () =>
    notify({ type: "precache-progress", done, count: PRECACHE.length, bytes, total });
  await report();
  for (const batch of batches()) {
    // "reload": a fixed file name (pyodide.asm.wasm) must not come from the HTTP cache
    await cache.addAll(batch.map((i) => new Request(PRECACHE[i], { cache: "reload" })));
    done += batch.length;
    bytes += batch.reduce((a, i) => a + (BYTES[i] || 0), 0);
    await report();
  }
  await notify({ type: "precache-done" });
}

self.addEventListener("install", (event) => {
  // no skipWaiting here: a new version waits until the page asks for it
  event.waitUntil(precache());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      for (const name of await caches.keys()) {
        if (name.startsWith(PREFIX) && name !== CACHE) await caches.delete(name);
      }
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request, { ignoreSearch: true });
  if (hit) return hit;
  try {
    const response = await fetch(request);
    if (response.ok && response.status === 200) cache.put(request, response.clone());
    return response;
  } catch (err) {
    if (request.mode === "navigate") {
      const shell = await cache.match(new URL("./", self.registration.scope).href);
      if (shell) return shell;
    }
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  if (new URL(request.url).origin !== self.location.origin) return;
  event.respondWith(cacheFirst(request));
});
