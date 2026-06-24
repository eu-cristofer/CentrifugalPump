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

**Canvas twin.** If a notebook has a sibling `.pumpflow` project that wires the
same flow as nodes, keep both in this folder and link the `.pumpflow` from the
intro (see `UC-06_affinity_speed_change.ipynb` ↔ `example_1.pumpflow`).

## Contents

| Notebook | Use case | Demonstrates |
|---|---|---|
| [`UC-06_affinity_speed_change.ipynb`](UC-06_affinity_speed_change.ipynb) | [UC-06](../docs/product/use-cases.md) | Affinity speed correction of measured test points to 2000 & 1750 rpm, degree-3 fit, overlay plot (canvas twin: [`example_1.pumpflow`](example_1.pumpflow)) |
