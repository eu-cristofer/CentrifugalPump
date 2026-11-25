# PumpLab / PumpFlow — Release Notes

**Version:** 0.1.0  ·  **Date:** 5 June 2026  ·  **Branch:** `orange`
**Component:** `pumpflow/` — visual workflow front-end for the `pump` library

---

## Summary

PumpFlow `0.1.0` introduces an **Orange3-style node-canvas desktop application**
that implements `UI_SPEC.md` end to end: engineers wire seven workflow widgets on
a canvas to take an API 610 pump from rated point + measured FAT data → affinity/
density correction → curve fit → live plots → an **APPROVED/REJECTED** verdict →
a `.docx`/`.json` report. It is a thin, reactive UI layer that delegates all
physics to the existing `pump` library.

---

## Key Highlights

- 🧩 **Visual node canvas** — drag widgets, wire typed ports, and watch results
  propagate downstream automatically (reactive topological recompute).
- 🔬 **All seven UI_SPEC §5 widgets** shipped, each with a double-click property
  dialog: Rated Point Input, Test Points Table, Speed/Affinity Correction, Curve
  Fit, Performance Plot, API 610 Compliance Check, Report Export.
- ⚖️ **API 610 verdict** with editable tolerances, per-parameter deviation table,
  and a bold pass/fail banner — numbers sourced from `PerformanceChecker`.
- 🔀 **Two-pump A/B case** — fan-out from one shared Rated Point and merge multiple
  branches into one consolidated Report Export (multi-connection input).
- 💾 **Two file formats** — `.pumpflow` project files (full canvas) and the
  UI_SPEC §6.2 data-exchange JSON (locale comma-decimals supported).
- 📈 **Embedded Matplotlib** plots (Q×H, Q×P, Q×η) with polynomial + natural cubic
  spline overlays and a rated-capacity crosshair; PNG export.
- 📦 **Minimal dependency tree** — PySide6 + matplotlib + numpy + `pump`
  (no NodeGraphQt, no Orange3 runtime), per UI_SPEC §8.

---

## Changelog

### New Features

- **Reactive node graph** (`pumpflow/canvas/`): `QGraphicsView` scene with
  draggable nodes, bezier links, typed ports, fan-out and multi-connection merge,
  rubber-band selection, pan/zoom, and a dotted engineering grid.
- **Topological evaluation engine** (`canvas/scene.py::GraphScene.evaluate`):
  recomputes every node in dependency order whenever a value, link, or setting
  changes, surfacing per-node status (`idle`/`ok`/`invalid`/`error`/`reject`).
- **Seven widget nodes** (`pumpflow/nodes/`), each emitting a typed signal:
  - `rated_point.py` — Rated Point Input (source; shared design point + fluid).
  - `test_points.py` — Test Points Table (editable grid; paste; live computed
    `Head` and `η` columns; ≥3-point and shut-off validation).
  - `correction.py` — Speed/Affinity + density correction with before/after table.
  - `curve_fit.py` — polynomial (primary) + natural cubic spline (secondary) with
    coefficients and R² readout.
  - `performance_plot.py` — stacked Q×H/Q×P/Q×η charts, toggles, PNG export.
  - `compliance.py` — API 610 deviation table, editable tolerances, verdict banner.
  - `report_export.py` — branch-grouped `.docx` (via `ReportGenerator`), `.json`,
    and `.png` export.
- **Typed signal payloads** (`signals.py`): immutable dataclasses
  (`RatedPoint`, `TestPointSet`, `CorrectedCurve`, `FittedModel`,
  `ComplianceResult`, `ReportBundle`) with the identity convention from UI_SPEC §3
  (shared service TAG vs. per-branch pump TAG).
- **Library binding layer** (`binding.py`): the single boundary that calls `pump`
  (`Fluid`, `DesignPoint`, `TestPoint`, `PerformanceCurve.to_speed/.to_fluid/
  fitter/predict_*`, `PerformanceChecker`, `ReportGenerator`).
- **Ported maths** (`mathx.py`): `NaturalCubicSpline` and `water_density_kgm3`,
  per the UI_SPEC §4 note (not yet in `pump`).
- **Persistence** (`persistence.py` + `scene.py`): `.pumpflow` project save/load
  and UI_SPEC §6.2 data-exchange JSON import/export.
- **Default pre-wired pipeline + A/B demo** (`app.py`): launches populated with
  seeded single-pump data; `Canvas ▸ Add Pump B branch` adds the second unit.
- **`python -m pumpflow`** entry point with a light industrial-steel theme.

### Improvements

- **Locale-tolerant number parsing** (`numfmt.py`): accepts `,` or `.` decimals
  and thousands separators, used live in the test grid and the JSON importer.
- **Scrollable property dialogs** with consistent header/section/banner styling.
- **Tolerant port hit-testing** (14 px radius) so links are easy to grab.
- **Single-fluid handling**: per-row `Head`/`η` computed with each row's own water
  density, then pinned onto `TestPoint`s, satisfying the library's one-fluid-per-
  curve constraint while preserving correct correction behaviour.

### Bug Fixes

> First release — no prior versions. The items below are notable fixes made
> against in-development drafts during this release's construction.

- Moved all edge-drag handling from the port/scene into `GraphView` to avoid a Qt
  mouse-grabber conflict that prevented links from completing on release.
- Widened `NodeItem.boundingRect` margins so ports/shadows are not clipped.
- Removed an invalid conditional-import line in `report_export.py` and a stray
  paint statement in the grid renderer.

---

## Breaking Changes / Migration Guide

This is the **initial `0.1.0` release**, so there are no breaking changes for
existing PumpFlow users. To adopt it in the `CentrifugalPump` repo:

1. **Place the package** — copy the `pumpflow/` folder to the repo root, next to
   `pump/`:
   ```text
   CentrifugalPump/
   ├── pump/
   ├── pumpflow/        ← add this
   └── ...
   ```
2. **Install the library** (provides `pint`, `python-docx`, `tabulate`):
   ```bash
   pip install -e .
   ```
3. **Install UI dependencies:**
   ```bash
   pip install PySide6 matplotlib numpy
   ```
4. **Run:**
   ```bash
   python -m pumpflow
   ```
5. **`.docx` templates** — Report Export calls `pump.ReportGenerator`, which needs
   `template_en.docx` / `template_pt.docx`. If they are not on the install path,
   set a template file in the Report Export dialog's *Template* field.

### Notes for library maintainers

- **`mathx.py` is a temporary home.** `NaturalCubicSpline` and `water_density_kgm3`
  live in the UI because they are not in `pump` yet (UI_SPEC §4 note). If/when they
  move into `pump`, update `binding.py`/`nodes/plotting.py` imports and delete the
  UI copies. If the reference notebook has exact `water_density_kgm3` coefficients,
  replace the placeholder polynomial in `mathx.py`.
- **Single-fluid assumption.** `PerformanceCurve` takes one `Fluid` for all points;
  PumpFlow works within that. If `pump` later supports per-point fluids, the
  pinning workaround in `binding.correct_curve` can be simplified.
- **Viscosity correction** is shown but disabled in the Correction dialog pending
  a library implementation.
