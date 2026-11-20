# Sprint 4 — Web scaffold + offline Pyodide spike (parity gate)

## Goal
Prove, before any UI work, that the unchanged Python runs offline in Pyodide and
gives the desktop's answers.  Set up the `web/` project.

## Files
- `web/` (new): Vite + React 18 + TypeScript (strict), React Flow (`@xyflow/react`),
  Vitest, ESLint.  Exact versions pinned in `package.json` + `package-lock.json`.
  Scripts: `dev`, `build`, `check` (tsc --noEmit, eslint, vitest run), `vendor`,
  `parity`.
- `web/scripts/vendor.mjs` — fills `web/public/py/` (git-ignored) with:
  the Pyodide distribution (from the pinned `pyodide` npm package, core + the
  packages needed: numpy, matplotlib, lxml, openpyxl, and their deps);
  pure-Python wheels for pint, flexcache, flexparser, tabulate, python-docx,
  typing-extensions (downloaded once with `pip download --only-binary=:all:
  --platform any --no-deps -d …` — **build time only**);
  the project wheel built by `python -m build --wheel` (contains `pump` +
  `pumpflow` + standards TOML + locales + templates + design tokens).
  Writes `web/public/py/manifest.json` (file list + sha256).
- `web/src/engine/worker.ts` — Web Worker: `loadPyodide({indexURL: "/py/"})`,
  `loadPackage` from local files only, `micropip.install` the local wheels with
  `deps=False`, `import pumpflow.webapi`, then serves `{id, fn, args}` →
  `{id, result | error}` messages for `catalog`, `evaluate`, `default_settings`,
  `export_report`.
- `web/src/engine/client.ts` — typed promise wrapper; `web/src/engine/types.ts` —
  TypeScript types mirroring the `pumpflow.webapi` docstring.
- `web/src/App.tsx` — minimal page: loading progress, "Open .pumpflow" file input,
  then a plain table of node id / kind / state / status (no canvas yet).
- `web/scripts/parity.mjs` — runs Pyodide **in Node** with the same vendored files,
  evaluates `examples/user/B-34004A_MRT_reference.pumpflow` and every
  `tests/fixtures/v1/*.pumpflow`, and compares states/statuses with
  `tests/fixtures/v1/expected.json` and with `python -m pumpflow.export_cli`
  output; exits 1 on any difference.
- `web/scripts/tokens.mjs` — generates `web/src/tokens.css` (CSS variables) from
  `pump/design/tokens.json` at build time.
- `.gitignore`: `web/node_modules/`, `web/public/py/`, `web/dist/`.
- `pyproject.toml`: make sure package data (TOML standards, locales `.po`, docx
  templates, `pump/design/tokens.json`) is in the wheel.

## Reuse
- `pumpflow.webapi` (sprint 3) — the only Python entry point the worker calls.
- `pump/design/tokens.json` — colours for `tokens.css`.

## Tests
- `npm --prefix web run parity` passes (this is the spike's go/no-go).
- Vitest: `client.ts` request/response matching (mock worker); `tokens.css` contains
  `--accent`.
- Network guard: a Vitest/Node check that `web/src` and `web/index.html` reference no
  `http://` or `https://` URLs (offline rule).

## Acceptance
```bash
pytest -q
npm --prefix web ci && npm --prefix web run vendor && npm --prefix web run check
npm --prefix web run parity
npm --prefix web run build
```

## Definition of done
Opening a `.pumpflow` in the dev server lists the same node statuses as the desktop,
with the network disabled after the page loads.  If parity fails for a reason that
cannot be fixed within the sprint (a package missing from Pyodide), write
`BLOCKED:` with the package and stop: the project's viability is the point.

## Assumes
Sprint 3: `pumpflow.webapi` with `catalog/evaluate/default_settings/export_report`.
Node ≥ 20 and npm available (checked 2026-11-20: Node 26.7, npm 11.19).
