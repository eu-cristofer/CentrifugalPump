// Fills web/public/py/ with everything the browser needs to run the Python
// engine offline.  This is the ONLY script allowed to use the network, and it
// runs at build time only.  Usage: node scripts/vendor.mjs
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, "..");
const repoRoot = path.resolve(webRoot, "..");
const pyDir = path.join(webRoot, "public", "py");
const wheelDir = path.join(pyDir, "wheels");
const python = process.env.PYTHON || "python3";

const PYODIDE_VERSION = "314.0.7";
const CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const CORE = [
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
];
const ROOT_PACKAGES = ["numpy", "matplotlib", "lxml", "typing-extensions", "platformdirs"];
const PURE_WHEELS = [
  ["Pint", "0.25.3"],
  ["flexcache", "0.3"],
  ["flexparser", "0.4"],
  ["python-docx", "1.2.0"],
  ["openpyxl", "3.1.5"],
  ["et_xmlfile", "2.0.0"],
  ["tabulate", "0.10.0"],
];

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const norm = (name) => name.toLowerCase().replace(/[-.]/g, "_");

mkdirSync(wheelDir, { recursive: true });

// 1. Core files from the pinned npm package.
const npmPkg = path.join(webRoot, "node_modules", "pyodide");
if (!existsSync(npmPkg)) throw new Error("node_modules/pyodide missing: run npm ci first");
const npmVersion = JSON.parse(readFileSync(path.join(npmPkg, "package.json"), "utf8")).version;
if (npmVersion !== PYODIDE_VERSION) {
  throw new Error(`pyodide npm package is ${npmVersion}, expected ${PYODIDE_VERSION}`);
}
for (const f of CORE) copyFileSync(path.join(npmPkg, f), path.join(pyDir, f));
console.log(`core: ${CORE.length} files`);

// 2. Package closure from pyodide-lock.json, downloaded and verified.
const lock = JSON.parse(readFileSync(path.join(pyDir, "pyodide-lock.json"), "utf8"));
const lockPkgs = lock.packages;
const closure = [];
const seen = new Set();
const visit = (name) => {
  const key = name in lockPkgs ? name : name.toLowerCase();
  if (seen.has(key)) return;
  const entry = lockPkgs[key];
  if (!entry) throw new Error(`package ${name} not in pyodide-lock.json`);
  seen.add(key);
  for (const dep of entry.depends ?? []) visit(dep);
  closure.push(key);
};
ROOT_PACKAGES.forEach(visit);

for (const name of closure) {
  const { file_name: fileName, sha256: want } = lockPkgs[name];
  const target = path.join(pyDir, fileName);
  if (!existsSync(target)) {
    console.log(`download ${fileName}`);
    const res = await fetch(CDN + fileName);
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${CDN + fileName}`);
    writeFileSync(target, Buffer.from(await res.arrayBuffer()));
  }
  const got = sha256(readFileSync(target));
  if (got !== want) {
    rmSync(target);
    throw new Error(`sha256 mismatch for ${fileName}: ${got} != ${want}`);
  }
}
console.log(`packages: ${closure.length} (${closure.join(", ")})`);

// 3. Pure-Python wheels.
const present = (name, version) =>
  readdirSync(wheelDir).some((f) => f.toLowerCase().startsWith(`${norm(name)}-${version}-`));
if (!PURE_WHEELS.every(([n, v]) => present(n, v))) {
  execFileSync(
    python,
    [
      "-m",
      "pip",
      "download",
      "--no-deps",
      "--only-binary=:all:",
      "-d",
      wheelDir,
      ...PURE_WHEELS.map(([n, v]) => `${n}==${v}`),
    ],
    { stdio: "inherit" },
  );
}

// 4. Project wheel (pump + pumpflow + data files).
for (const f of readdirSync(wheelDir)) {
  if (/^centrifugal[_-]pump-.*\.whl$/i.test(f)) rmSync(path.join(wheelDir, f));
}
execFileSync(python, ["-m", "build", "--wheel", "--outdir", wheelDir, repoRoot], {
  stdio: "inherit",
});

// 5. Manifest.
const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)],
  );
const files = walk(pyDir)
  .filter((p) => path.basename(p) !== "manifest.json")
  .sort()
  .map((p) => ({
    path: path.relative(pyDir, p).split(path.sep).join("/"),
    sha256: sha256(readFileSync(p)),
    bytes: statSync(p).size,
  }));
const wheels = readdirSync(wheelDir).filter((f) => f.endsWith(".whl")).sort();
const manifest = { pyodide: PYODIDE_VERSION, packages: closure, wheels, files };
writeFileSync(path.join(pyDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`manifest: ${files.length} files, ${wheels.length} wheels`);
