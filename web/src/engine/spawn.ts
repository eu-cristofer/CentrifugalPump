import { Engine } from "./client";
import type { Progress } from "./types";

/** Start the engine worker (browser only). */
export function spawnEngine(onProgress?: (progress: Progress) => void): Engine {
  const worker = new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });
  return new Engine(worker, onProgress);
}
