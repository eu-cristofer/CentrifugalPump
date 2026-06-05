# ADR 0004 — Refactor `PerformanceCurve`: split plotting from computation

- **Status:** Proposed
- **Criticality:** 🟠 High
- **Date:** 2026-06-05
- **Related:** [Architecture §4.4](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)
- **Depends on:** [ADR 0001](0001-establish-automated-test-harness.md)

## Context

[`pump/performance_curve.py`](../../pump/performance_curve.py) is ~775 lines and
`PerformanceCurve` carries too many responsibilities:

- `plot_performance_curve` is a single ~160-line method interleaving data
  generation, Matplotlib axis styling, crosshair annotation, y-limit handling,
  and `BytesIO` export. It is the most fragile, hardest-to-test code in the repo.
- Three near-identical methods (`predict_head`/`predict_efficiency`/
  `predict_breaking_power`) and three near-identical `PerformanceFitter`
  properties (`head_coeffs`/`efficiency_coeffs`/`power_coeffs`) repeat the same
  shape with a different metric.

This concentrates change-risk and makes numeric behaviour impossible to test
without rendering a figure.

## Decision

1. **Extract a pure data method** `curve_samples(n=100)` that returns the
   smooth (capacity, head, power, efficiency) arrays and any fitted markers —
   no Matplotlib. `plot_performance_curve` becomes a thin renderer over it.
2. **Parameterize the triplets.** Replace the three `predict_*` with one
   `predict(metric, capacity)` (keeping thin named wrappers for back-compat), and
   drive the fitter's coefficient properties from a small metric registry.
3. Keep the public API stable; add deprecation shims only if signatures change.

## Consequences

**Positive**
- Numeric paths become unit-testable without a display.
- ~40 % of the duplication in the file collapses; future metrics are one entry.
- Rendering bugs are isolated from computation bugs.

**Negative**
- Touches the most-used class — **must** be done under ADR 0001's test net.
- Minor risk to notebooks that call `plot_performance_curve` with specific
  kwargs; preserve the existing signature.

## Acceptance

- `curve_samples()` covered by tests pinning array shapes and a couple of values.
- Existing example notebooks still render identically (visual spot-check).
