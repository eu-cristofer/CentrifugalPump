# 002_web — PumpFlow in the browser (offline, witness flow first)

Brings the FAT witness workflow of PumpFlow to the browser with no server: the
unchanged `pump` library and the `pumpflow` node logic run in **Pyodide** inside
a Web Worker, behind a React Flow + TypeScript front end, bundled **offline**
(no CDN, no network after install).  Scope is the witness pipeline used by the
B-34004 projects: Rated Point, Fluid, Test Points, Speed correction, Curve fit,
Performance plot, Compliance, NPSH, MRT Log, MRT Check, Report Export and Note.
The other node kinds load and evaluate but get no web form yet.

See [MOTIVATION.md](MOTIVATION.md) for the why, the decisions and the risks.

Status: ready to archive · Branch: feat/web · Baseline commit: d0d6749

# 002_web — Loop Protocol

Each run MUST:
1. Read this README top to bottom. Pick the FIRST sprint whose checkbox is `[ ]`.
   Never skip ahead; never start a sprint whose predecessor is unchecked.
2. Open its sprint-N.md and verify the "Assumes" line against the code. If an
   assumption fails, fix forward only if trivial; otherwise write
   `BLOCKED: <reason>` under the tracker line and STOP (do not tick).
3. Implement exactly the sprint's scope (via `/sprint-loop next 002_web` or
   `/sprint-loop run 002_web`: the drafter drafts, the orchestrator
   reviews/applies). Resist scope creep.
4. Run the sprint's Acceptance commands — all must pass.
5. Update the changelog (one bullet per user-visible change).
6. Tick the checkbox `[x]` and append `— done YYYY-MM-DD`.
7. Commit in one commit: `002_web sprint N: <title>`.
8. When all sprints are checked, mark the project `Status: ready to archive` and
   archive it later with `/sprint-loop archive 002_web`.

## Standing rules (every sprint)

- **One engine.** Physics and verdicts stay in `pump/` (ADR 0012); node logic stays in
  `pumpflow/nodes/*.compute`.  The browser **never** re-implements a calculation or a
  verdict in TypeScript: it sends a `.pumpflow` document to Python and displays what
  comes back.
- **Same answers.** Desktop, headless engine and browser must produce identical node
  states and statuses for `examples/user/B-34004A_MRT_reference.pumpflow` and
  `tests/fixtures/v1/expected.json`.
- **Offline and private.** No request leaves the browser at run time: no CDN, no
  analytics, no fonts from the network.  Customer data stays on the machine.
- **Design tokens.** Web colours, radii and font sizes come from
  `pump/design/tokens.json` (generated CSS variables); no hex literals in `web/src`.
- **Gates.** `pytest` green; black on new Python files and the CI list; from sprint 4,
  `npm --prefix web run check` (typecheck + lint + tests) green.
- **Regression fixture.** `python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf` exits 0.
- **Confidential material** (`examples/user/*.PDF`, `marker-output/`) never enters git
  or the web bundle.

## Tracker

- [x] [Sprint 1 — Headless graph engine](sprint-1.md) — done 2026-11-20
- [x] [Sprint 2 — Node logic importable without Qt](sprint-2.md) — done 2026-11-20
- [x] [Sprint 3 — JSON API for the browser (`pumpflow.webapi`)](sprint-3.md) — done 2026-11-20
- [x] [Sprint 4 — Web scaffold + offline Pyodide spike (parity gate)](sprint-4.md) — done 2026-11-20 (PARITY OK on 11 projects; Chrome boot 3.5 s)
- [x] [Sprint 5 — Canvas: open, view, wire, save](sprint-5.md) — done 2026-11-20
- [x] [Sprint 6 — Witness forms I: Rated Point, Fluid, Test Points, Correction, Fit, Compliance](sprint-6.md) — done 2026-11-20
- [x] [Sprint 7 — Witness forms II: plots, NPSH, MRT Log, MRT Check, Note](sprint-7.md) — done 2026-11-20
- [x] [Sprint 8 — Reports in the browser + installable offline app](sprint-8.md) — done 2026-11-20 (hosting choice still open, see MOTIVATION.md)
- [x] [Sprint 9 — CI parity job, docs and training](sprint-9.md) — done 2026-11-20
