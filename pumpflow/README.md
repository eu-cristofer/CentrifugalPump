# PumpFlow — API 610 Pump Performance Workbench

An Orange3-style **node-canvas** desktop app implementing `UI_SPEC.md` on top of
the existing `pump` library. Drag widgets onto a canvas, wire them together, and
data flows along the links: rated point + measured test points → affinity/density
correction → curve fit → plots, an API 610 APPROVED/REJECTED verdict, and a
`.docx`/`.json` report.

> Built natively on **PySide6 (QGraphicsView)** — no NodeGraphQt, no Orange3
> runtime — so it stays a small, self-contained tool with a minimal dependency
> tree (PySide6 + matplotlib + numpy + `pump`), exactly as UI_SPEC §8 asks.

---

## Install & run

```bash
# 1) install the engineering library (brings pint, python-docx, tabulate)
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
git checkout orange
pip install -e .

# 2) install the UI deps and drop this `pumpflow/` package at the repo root
pip install PySide6 matplotlib numpy

# 3) run
python -m pumpflow
```

The app opens with the **default pre-wired pipeline** (UI_SPEC §2) already
populated with a realistic seeded single-pump dataset, so you immediately see
corrected points, fitted curves and a verdict. Double-click any node to open its
property dialog.

---

## What maps to the spec

| UI_SPEC | Where |
|---|---|
| §3 Signals | `pumpflow/signals.py` (immutable dataclasses) |
| §4 Library binding | `pumpflow/binding.py` (the *only* place that calls `pump`) |
| §4 note (spline, water density) | `pumpflow/mathx.py` |
| §5.1 Rated Point Input | `pumpflow/nodes/rated_point.py` |
| §5.2 Test Points Table | `pumpflow/nodes/test_points.py` |
| §5.3 Speed/Affinity Correction | `pumpflow/nodes/correction.py` |
| §5.4 Curve Fit | `pumpflow/nodes/curve_fit.py` |
| §5.5 Performance Plot | `pumpflow/nodes/performance_plot.py` |
| §5.6 API 610 Compliance Check | `pumpflow/nodes/compliance.py` |
| §5.7 Report Export | `pumpflow/nodes/report_export.py` |
| §6.1 Project file (`.pumpflow`) | `pumpflow/canvas/scene.py` (`to_dict`/`load_dict`) + `File ▸ Save/Open` |
| §6.2 Data-exchange JSON | `pumpflow/persistence.py` + `File ▸ Import/Export data file` |
| reactive recompute (§3/§7) | `pumpflow/canvas/scene.py` (`evaluate`, topological) |

## Canvas controls

- **Double-click** a node → property dialog (settings + live preview).
- **Drag from a port** → wire a link. Output ports **fan out**; the Report Export
  branch input is **multi-connection** (merge). Drag a single input off to re-wire.
- **Delete / Backspace** removes the selected nodes or links.
- **Wheel** zooms, **middle-drag** or **Alt+drag** pans.
- `Canvas ▸ Add Pump B branch` demonstrates the **A/B two-pump** case (UI_SPEC §2):
  a second Test Points Table sharing the one Rated Point and merging into the one
  Report Export.

## Two engineering notes

1. **Shared-fluid constraint.** `PerformanceCurve` requires one `Fluid` for all
   points. Per-row `Head` and `η` are computed with each row's own water density
   (UI_SPEC §5.2) and pinned onto the `TestPoint`s (`_head`/`_efficiency`), so the
   curve's single test-water fluid is only a label — correction to rated speed and
   rated density then follows the library's `to_speed` → `to_fluid` path exactly.
2. **Spline & water density** are ported into `mathx.py` because they are not in
   `pump` yet (UI_SPEC §4 note). The polynomial degree-3 fit remains the API-610
   primary; the natural cubic spline is the optional secondary overlay. If the
   notebook ships exact `water_density_kgm3` coefficients, drop them into
   `mathx.py`.

## `.docx` export

`Report Export ▸ Export .docx` calls `pump.ReportGenerator`. It needs the
library's `templates/template_en.docx` / `template_pt.docx`; if they aren't on the
install path, set a template file explicitly in the Report Export dialog.
