// Spike go/no-go: evaluate the reference projects in Pyodide (Node) and compare
// with the desktop Python (webapi.evaluate in a normal interpreter) and with
// tests/fixtures/v1/expected.json.  Exits 1 on any difference.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { boot } from "../src/engine/boot.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const repoRoot = path.resolve(webRoot, "..");
const pyDir = path.join(webRoot, "public", "py");
const python = process.env.PYTHON || "python3";

if (!existsSync(path.join(pyDir, "manifest.json"))) {
  console.error("web/public/py is empty: run `npm run vendor` first");
  process.exit(1);
}

const fixtureDir = path.join(repoRoot, "tests", "fixtures", "v1");
const rel = (p) => path.relative(repoRoot, p).split(path.sep).join("/");
const files = [
  ...readdirSync(fixtureDir)
    .filter((f) => f.endsWith(".pumpflow"))
    .sort()
    .map((f) => path.join(fixtureDir, f)),
  path.join(repoRoot, "examples", "user", "B-34004A_MRT_reference.pumpflow"),
  path.join(repoRoot, "examples", "user", "B-34004B_witness_2026-11-19.pumpflow"),
].map(rel);

const expected = JSON.parse(readFileSync(path.join(fixtureDir, "expected.json"), "utf8"));

// Desktop reference: one interpreter, all files.
const script = `
import json, sys
from pumpflow import webapi
out = {}
for p in sys.argv[1:]:
    with open(p, encoding="utf-8") as f:
        out[p] = webapi.evaluate(json.load(f))
print(json.dumps(out, allow_nan=False))
`;
const stdout = execFileSync(python, ["-c", script, ...files], {
  cwd: repoRoot,
  env: { ...process.env, QT_QPA_PLATFORM: "offscreen" },
  maxBuffer: 1 << 30,
  encoding: "utf8",
});
const desktop = JSON.parse(stdout.trim().split("\n").at(-1));

// Pyodide in Node, same boot code as the browser worker.
const { loadPyodide } = await import(pathToFileURL(path.join(pyDir, "pyodide.mjs")).href);
const engine = await boot({
  loadPyodide,
  indexURL: pyDir + path.sep,
  readFile: async (p) => new Uint8Array(await readFile(path.join(pyDir, p))),
  onProgress: (stage, loaded, total) => console.log(`boot ${stage} ${loaded}/${total}`),
});

const ABS = 1e-12;
const REL = 1e-9;
const same = (a, b) => {
  if (typeof a === "number" && typeof b === "number") {
    return Math.abs(a - b) <= ABS + REL * Math.max(Math.abs(a), Math.abs(b));
  }
  return JSON.stringify(a) === JSON.stringify(b);
};

const diffs = [];
const summary = [];

for (const file of files) {
  const doc = JSON.parse(readFileSync(path.join(repoRoot, file), "utf8"));
  const web = JSON.parse(engine.call("evaluate", [doc]));
  const ref = desktop[file];
  const before = diffs.length;
  const note = (msg) => diffs.push(`${file}: ${msg}`);

  const webIds = Object.keys(web.nodes).sort();
  const refIds = Object.keys(ref.nodes).sort();
  if (JSON.stringify(webIds) !== JSON.stringify(refIds)) note("node id sets differ");
  if (JSON.stringify(web.errors) !== JSON.stringify(ref.errors)) note("errors list differs");

  for (const id of refIds) {
    const w = web.nodes[id];
    const r = ref.nodes[id];
    if (!w) continue;
    for (const key of ["kind", "state", "status"]) {
      if (w[key] !== r[key]) {
        note(`${id}.${key}: pyodide ${JSON.stringify(w[key])} != desktop ${JSON.stringify(r[key])}`);
      }
    }
    if (JSON.stringify(w.badge) !== JSON.stringify(r.badge)) note(`${id}.badge differs`);
    if (r.kind === "compliance" && Array.isArray(r.view?.rows)) {
      const wr = w.view?.rows ?? [];
      if (wr.length !== r.view.rows.length) note(`${id}: compliance row count differs`);
      r.view.rows.forEach((row, i) => {
        for (const key of ["predicted", "min", "max"]) {
          if (!same(wr[i]?.[key], row[key])) {
            note(`${id} row ${row.name} ${key}: pyodide ${wr[i]?.[key]} != desktop ${row[key]}`);
          }
        }
        if (wr[i]?.verdict !== row.verdict) note(`${id} row ${row.name} verdict differs`);
      });
    }
  }

  // expected.json pins kind / state / status of the committed fixtures.
  const pinned = file.startsWith("tests/fixtures/v1/") ? expected[path.basename(file)] : undefined;
  if (pinned) {
    for (const [id, [kind, state, status]] of Object.entries(pinned)) {
      const w = web.nodes[id];
      if (!w) note(`expected.json node ${id} missing`);
      else if (w.kind !== kind || w.state !== state || w.status !== status) {
        note(`expected.json ${id}: want [${kind}, ${state}, ${status}] got [${w.kind}, ${w.state}, ${w.status}]`);
      }
    }
  }

  summary.push({
    file,
    nodes: webIds.length,
    errors: web.errors.length,
    expected_json: pinned ? "checked" : "-",
    differences: diffs.length - before,
  });
}

console.table(summary);
if (diffs.length) {
  console.error(`PARITY FAILED: ${diffs.length} difference(s)`);
  for (const d of diffs) console.error("  " + d);
  process.exit(1);
}
console.log("PARITY OK");
