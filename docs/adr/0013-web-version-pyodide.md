# ADR 0013 — The web version: one engine in Pyodide, offline bundle

- **Status:** Accepted
- **Criticality:** 🟠 High
- **Date:** 2026-11-20
- **Related:** [ADR 0012](0012-single-performance-verdict-engine.md),
  [002_web](../changes/002_web/README.md),
  [MOTIVATION](../changes/002_web/MOTIVATION.md), [web.md](../web.md)

## Context

PumpFlow needs Python, PySide6 and a working install.  On a vendor's test bench that is
often impossible (locked corporate machines, no admin rights, borrowed laptops), and a
browser is always there.  Customer data (datasheets, test results) must not leave the
machine.  The witness flow (twelve node kinds) must give the same verdicts as the desktop,
which ADR 0012 makes the single source of every verdict.

## Decision

- **Unchanged Python in Pyodide.**  `pump` and the `pumpflow` node logic run in a Web
  Worker.  The browser gets the same engine, so the same verdicts.
- **Qt-free engine and a JSON boundary.**  Graph evaluation moves to `pumpflow/engine.py`
  (shared by the canvas, `export_cli`, the tests and the browser).  Node modules import Qt
  only inside their dialogs.  `pumpflow/webapi.py` takes a `.pumpflow` document and returns
  JSON (states, statuses, badges, views, report bytes).  TypeScript never computes.
- **Offline vendored bundle.**  `npm --prefix web run vendor` downloads Pyodide and the
  wheels once (the only step that uses the network) and builds the project wheel; a service
  worker caches the app.  No CDN, no network after install.
- **React Flow + TypeScript** (Vite) for the canvas and forms; uPlot for charts.
- **Witness-first scope.**  Twelve kinds have forms; the others load and evaluate and say
  "Edit this node in the desktop app".

## Alternatives rejected

- **A server (for example FastAPI).**  Customer data would have to leave the witness
  machine, and the bench may have no network.
- **A TypeScript rewrite.**  Two verdict engines that can drift; it breaks the rule of ADR
  0012.
- **An iOS/iPad native app.**  Considered and dropped on 2026-11-20 in favour of the web
  version, which also covers laptops.

## Consequences

- **Parity gate in CI.**  Job `web` runs `check`, `parity` and `build` on every push;
  `parity` fails if the browser and the desktop disagree on the fixture projects.
- **First load is about 30 MB** (mostly the Python engine); after that the app starts from
  the cache (engine ready in 3.5 s in Chrome on the repo build).
- **LaTeX and PDF reports stay desktop only** (they need a LaTeX installation).  The
  browser offers Word, HTML, xlsx and "Print to PDF".
- **Desktop helpers shared with the web:** `pump_type_hint`, `paste_rows`,
  `banner_message`, `viscous_summary`, `param_cells` and `mechanical_run.paste_rows`, so
  both front ends show the same strings.
- **Rebuild step.**  After a change to Python used by the web, run `npm --prefix web run
  vendor` and `npm --prefix web run parity`.
- **Hosting is open** (owner's call): the build is host-neutral and must be served at the
  origin root.
