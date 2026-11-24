# Use-case worked examples

Runnable notebooks that demonstrate the registry use cases in
[`docs/product/use-cases.md`](../docs/product/use-cases.md). Each one takes a
realistic input, drives the **`pump`** library end-to-end, and shows the result a
FAT engineer would read.

## Guidelines

**Name by the use case.** One notebook per use case (or per distinct scenario),
named `UC-NN_short_slug.ipynb` — e.g. `UC-06_affinity_speed_change.ipynb`. State
the UC and link the registry entry in the first markdown cell.

**Depend on `pump` only.** Use-case notebooks import **`pump`** plus `numpy` /
`matplotlib`. They must **not** import `pumpflow` — that is the GUI workbench, not
the physics. If a small piece of math the library doesn't host yet is needed
(e.g. water density vs temperature), define a short, clearly-labelled helper in
the notebook rather than reaching into `pumpflow`.

> A demonstration of the *visual workbench* belongs in [`../examples/`](../examples/)
> alongside its `.pumpflow` canvas project — not here.

**Pin measured values.** When you build `TestPoint`s from measured pressures,
compute Head/η yourself and pin them with `_head=` / `_efficiency=` so
`PerformanceCurve.to_speed` / `to_fluid` preserve the measurements instead of
re-deriving them.

**Structure.** Keep a predictable flow, each code cell preceded by a one- or
two-line "why" markdown cell:

1. Setup + any inline helpers
2. Inputs (the measured / rated data)
3. Computation (`PerformanceCurve`, `to_speed`/`to_fluid`, `fitter`, `predict_*`)
4. Plot
5. Readout / verdict

**Must run top-to-bottom.** A notebook has to pass *Restart & Run All* with no
manual setup. Where possible, assert the result against the use case's stated
**acceptance** (e.g. UC-06's `to_speed(N).to_speed(N0)` round-trip `< 1e-6`).
End every notebook with `assert` cells: the demo becomes a test, and
`pytest tests/test_notebooks.py` (marker `slow`) executes them all in CI.

**Generated notebooks.** `UC-01`, `UC-02`, `UC-03-04`, `UC-05`, `UC-07`, `UC-08`, `UC-09`,
`UC-11`, `viscosity_HI967` and `TR-01_witness_training` are written by [`build_notebooks.py`](build_notebooks.py)
from plain Python strings (`nbformat`). Edit the script, not the `.ipynb`, then run
`python use_cases/build_notebooks.py` and execute the notebooks. Write temporary output
(reports, catalogues) to a `tempfile.TemporaryDirectory`, never into the repo.

**Canvas twin.** If a notebook has a sibling `.pumpflow` project that wires the
same flow as nodes, keep both in this folder and link the `.pumpflow` from the
intro (see `UC-06_affinity_speed_change.ipynb` ↔ `example_1.pumpflow`).

## Contents

| Notebook | Use case | Demonstrates |
|---|---|---|
| [`UC-00_utilities_demo.ipynb`](UC-00_utilities_demo.ipynb) | [UC-00](../docs/product/use-cases.md) | The units/fluids foundation: normalising mixed-unit gauge readings through `quantity_factory`, pressure `context`, `Fluid`/`Water`, and a lossless round-trip acceptance |
| [`UC-01_selection.ipynb`](UC-01_selection.ipynb) | [UC-01](../docs/product/use-cases.md) | Pump selection: a `*.pumpcurve.json` catalogue, ranking for a duty (as-is / speed / trim), the preferred operating region and the rejections |
| [`UC-02_performance_verification.ipynb`](UC-02_performance_verification.ipynb) | [UC-02](../docs/product/use-cases.md) | P-9001A in native Vendor A units (gpm, psi, °F, hp): head and η per row, complete head, speed + density correction, API 610 8th + N-553 check |
| [`UC-03-04_system_operating_point.ipynb`](UC-03-04_system_operating_point.ipynb) | [UC-03 / UC-04](../docs/product/use-cases.md) | System curves (k·Qⁿ, two points, Darcy–Weisbach) and the operating point (poly / spline) |
| [`UC-05_npsh.ipynb`](UC-05_npsh.ipynb) | [UC-05](../docs/product/use-cases.md) | NPSHa from suction conditions, NPSHr curve, NPSH3 sweep, ratio / margin verdicts |
| [`UC-06_affinity_speed_change.ipynb`](UC-06_affinity_speed_change.ipynb) | [UC-06](../docs/product/use-cases.md) | Affinity speed correction of measured test points to 2000 & 1750 rpm, degree-3 fit, overlay plot (canvas twin: [`example_1.pumpflow`](example_1.pumpflow)) |
| [`UC-07_trim.ipynb`](UC-07_trim.ipynb) | [UC-07](../docs/product/use-cases.md) | Impeller trim of P-9001A to its rated duty (≈ 127.1 mm), affinity checks and limits |
| [`UC-08_compare.ipynb`](UC-08_compare.ipynb) | [UC-08](../docs/product/use-cases.md) | Twin pumps A vs B: deltas against the reference curve and the overlay plot |
| [`UC-09_reports.ipynb`](UC-09_reports.ipynb) | [UC-09](../docs/product/use-cases.md) | The FAT report as `.docx`, `.tex` and (with a TeX engine) `.pdf`, in en and pt |
| [`UC-11_mechanical_run.ipynb`](UC-11_mechanical_run.ipynb) | [UC-11](../docs/product/use-cases.md) | A 4 h mechanical run log: limits, stabilisation, duration and the verdicts |
| [`viscosity_HI967.ipynb`](viscosity_HI967.ipynb) | HI 9.6.7 | Viscosity correction: B, the factors, the corrected curve and the edge cases |
| [`TR-01_witness_training.ipynb`](TR-01_witness_training.ipynb) | Training [TR-01](../docs/training/TR-01-witness-performance-test.md) | Exercises for witnessing an API 610 performance test: tolerance bands by edition, efficiency, NPSH rules, vibration in RMS, test speed, the rising-curve rule; answers asserted |

The physics behind each notebook is explained in the [concept pages](../docs/concepts/affinity.md)
(affinity, head components, NPSH, viscosity, acceptance tolerances, system curve, mechanical run).
