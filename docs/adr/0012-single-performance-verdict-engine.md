# ADR 0012 — One performance-verdict engine, no silent passes

- **Status:** Accepted
- **Criticality:** 🟠 High
- **Date:** 2026-11-17
- **Related:** [ADR 0007](0007-remove-acl-private-state-leak.md),
  [acceptance tolerances](../concepts/acceptance-tolerances.md),
  code-review findings B1–B3 in [NEXT_STEPS](../changes/NEXT_STEPS.md)

## Context

The API 610 pass/fail verdict was computed twice:

- `pumpflow.binding.check_compliance` (the Compliance node and the reports);
- `pump.PerformanceChecker.check_summary` (the library and the notebooks).

Both read the same `AcceptanceCriteria`, but the logic (bands, overrides, efficiency, the
rising-curve rule) was duplicated, against the rule that `pumpflow` holds no physics.  The
library version also swallowed errors: when the power or efficiency prediction raised, the
row disappeared from the table, and `parallel_operation_ok()` returned `None`, which the
verdict treated as "not a failure".  A check that could not be made became a silent pass.

## Decision

- `pump.acceptance.evaluate_performance(curve, rated_q, rated_head, criteria, ...)` is the
  **only** implementation of the performance verdict.  It returns a `PerformanceVerdict`
  whose `CheckRow`s carry the status `pass`, `fail`, `info` (reported, not judged:
  efficiency without a purchaser tolerance) or `not evaluated` (required but not
  computable, with the reason in `note`).
- `approved = passed and complete`: a verdict is never an approval while a required check
  is `not evaluated`.  The workbench shows **NOT FULLY ASSESSED**, and so do the reports.
- `PerformanceChecker.verdict()`, `check_summary` and `parallel_operation_ok()` are views of
  the engine.  `binding.check_compliance` only converts rows to display floats.
- New check: **test speed** within `test_speed_tol` of the rated speed (API 610 8th
  4.3.3.2.3, 11th 8.3.3.3 c: 3 % unless otherwise agreed), using the measured speeds now
  carried on `FittedModel.test_speeds`.

## Consequences

- The library and the workbench cannot disagree on a verdict.
- New rules go in one place, together with their TOML data and tests.
- Compliance tables gain a "Test speed" row.  Saved projects are unaffected; the regression
  fixtures were updated to include that row.
