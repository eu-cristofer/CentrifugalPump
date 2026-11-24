# 002_web — Motivation

## Problem

PumpFlow needs Python, PySide6 and a working install on the witness's laptop.  At a
vendor's test bench that is often impossible (locked corporate machines, no admin
rights, borrowed laptops).  A browser is always there.  Customer data (datasheets,
test results) must not leave the machine, so a hosted server is not an option.

## Approach

- **Run the existing Python in the browser.**  `pump` and the `pumpflow` node
  `compute()` methods are already Qt-free in substance; their dependencies (numpy,
  matplotlib, pint, python-docx/lxml, tabulate, openpyxl) all exist for Pyodide.  The
  browser gets the same engine, so the same verdicts, with nothing re-implemented.
- **Make the engine headless first.**  Graph evaluation lives in the Qt
  `GraphScene`; it moves to a Qt-free `pumpflow.engine` that the desktop canvas, the
  export CLI, the tests and the browser all share.
- **One JSON boundary.**  `pumpflow.webapi` takes a `.pumpflow` document and returns
  node states, statuses, verdict badges, tables and chart series as plain JSON;
  reports come back as bytes.  The TypeScript side only renders and edits settings.
- **Witness flow first.**  The web forms cover the twelve node kinds the P-9001
  projects use; the rest evaluate but have no form yet.

## Decisions

- 2026-11-17 — web version explored (Pyodide feasible; LaTeX/PDF not in the browser);
  postponed.
- 2026-11-20 — iOS/iPad native app considered and dropped in favour of the web version.
- 2026-11-20 — scope: **witness flow first** (not all 18 node kinds).
- 2026-11-20 — delivery: **offline bundle** (~30 MB; Pyodide and wheels vendored, no CDN).
- 2026-11-20 — front end: **React Flow + TypeScript** (Vite build).
- 2026-11-23 — hosting: GitHub Pages (docs at the root, app under `app/`).
- 2026-11-20 — PDF: the browser prints the HTML report to PDF ("Print to PDF"); the
  LaTeX PDF stays desktop-only unless a later project changes that.

## Open decisions

None.  Hosting was decided on 2026-11-23 (project 003_public-split): GitHub Pages,
documentation at the site root and the app under `app/`, built with
`PUMPFLOW_BASE=/<repo>/app/` by `.github/workflows/pages.yml`.  Any other static host,
or localhost, still works with the default root build.

## Risks

- **Pyodide package gaps.** pint (and `flexcache`/`flexparser`) and `tabulate` are
  pure Python but not in the Pyodide distribution: they must be vendored as wheels.
  python-docx needs lxml (in Pyodide).  Sprint 4 is the spike that proves this before
  any UI work.
- **Bundle size and start-up.** ~30 MB and several seconds of first load; mitigated
  by a service worker cache and a loading screen with progress.
- **Hidden Qt coupling.** Node modules import PySide6 at module level; sprint 2 moves
  those imports into `create_dialog` and a test forbids regressions.
- **Two front ends drift.** The desktop dialogs and the web forms can diverge in
  labels and validation; UI_SPEC stays the single spec, and the parity gate covers
  results (not looks).
- **matplotlib in the worker** is slow to import; web charts use returned series
  (JS charts), matplotlib only runs for report export.
