# Sprint 7 — Witness forms II: plots, NPSH, MRT Log, MRT Check, Note

## Goal
Complete the witness flow: performance chart, NPSH, mechanical run log and check, and
notes, all from Python-computed data.

## Files
- `web/src/charts/` — a small chart component on **uPlot** (pinned version, bundled):
  Q×H, Q×P, Q×η panels + NPSHr, rated-point crosshair, measured points, fitted curve;
  colours from `chart-*` tokens; hover readout.  Series come from
  `node_view` (no curve evaluation in TypeScript).
- `web/src/forms/PerformancePlotForm.tsx` (show poly/spline/points, axis limits).
- `web/src/forms/NpshForm.tsx` — mode, points grid, NPSHa inputs, verdict banner.
- `web/src/forms/MrtLogForm.tsx` — channel columns (name, dimension, unit, role),
  timestamped rows every N minutes ("Add reading" pre-fills the next time), paste.
- `web/src/forms/MrtCheckForm.tsx` — check rows, verdict, overrides.
- `web/src/forms/NoteForm.tsx` — Markdown editor + preview (sanitised; no remote
  images), "Include in report" toggle.
- `pumpflow/webapi.py` — extend `node_view` if a chart or table needs more data; tests.

## Reuse
- `pumpflow/nodes/performance_plot.py`, `npsh.py`, `mechanical_run.py`,
  `mechanical_run_check.py`, `markdown_note.py` (`create_dialog` field lists and the
  data they plot); `pumpflow/nodes/plotting.py` (series and colours).

## Tests
- Vitest: chart renders the series lengths it is given; MRT "Add reading" time step.
- pytest: `node_view` for npsh / mechanical_run_check / performance_plot is JSON-safe
  and matches desktop numbers for B-34004A (NPSHr 1.08 m @ rated, ratio 2.22; MRT
  FAILED (unverified limits)).

## Acceptance
```bash
pytest -q
npm --prefix web run check && npm --prefix web run parity && npm --prefix web run build
```

## Definition of done
The whole B-34004B witness day (performance, NPSH, 4 h MRT, notes) can be entered and
judged in the browser.

## Assumes
Sprint 6: form panel, fields, unit helpers.
