# Sprint 10 — UC-07 Impeller trim

## Goal
Predict performance at a trimmed or enlarged impeller diameter using diameter affinity:
- Q ∝ D;
- H ∝ D²;
- P ∝ D³;
- η invariant within small trims.

Range warnings apply, and the result is visible in the GUI and the report.

## Files
- `pump/performance_curve.py`:
  - `PerformanceCurve.to_diameter(d_new, d_ref) -> PerformanceCurve`, a **new instance**;
  - structure it after `to_speed` (`:441-510`): the same TestPoint rebuild, passing `_head`/`_efficiency` to preserve measured values;
  - warn when |1 − d_new/d_ref| > 5 % (configurable `max_trim`), since affinity accuracy degrades with large trims;
  - remove the dead commented block in `to_speed` (`:492-495`).
- `pump/point.py` / `DesignPoint`: optional `impeller_diameter`, plus `impeller_diameter_max`/`_min` (Quantities).
- `pumpflow/signals.py` `RatedPoint`: `impeller_diameter`, `impeller_diameter_max`, `impeller_diameter_min` (optional). Migration: absent.
- `pumpflow/nodes/rated_point.py`: three length `UnitField`s.
- `pumpflow/nodes/trim.py` (new node `trim`, registered):
  - input FittedModel / CorrectedCurve plus RatedPoint;
  - target diameter `UnitField`, or "solve for rated head": the diameter that passes through rated (Q, H) along the affinity parabola H = (H_r/Q_r²)·Q², found by root-finding on the fitted curve;
  - outputs a CorrectedCurve tagged `<pump_tag>@D=…`.
- `pump/trim.py` (new): `diameter_for_duty(curve, q, h, d_ref)` uses the affinity parabola intersection, solved with `numpy.roots` on the fitted polynomial minus the parabola, picking the real root in the tested range. SciPy is not a dependency and must not be added.
- B-34004A datasheet: impeller nominal 128 mm, max 131, min 125 (I-FD-5290.00-22315-311-SWM-001 rev B line 28). Add these to the rated point.

## Reuse
- `PerformanceCurve.to_speed` (`pump/performance_curve.py:441`).
- The `tests/test_affinity.py` round-trip pattern.
- `pumpflow/nodes/correction.py` as the node template.

## Tests
`tests/test_trim.py`:
- `curve.to_diameter(D2, D1).to_diameter(D1, D2)` ≈ the original (< 1e-6 at corresponding Q);
- head scales by (D2/D1)² at the corresponding Q;
- a warning beyond `max_trim`;
- `diameter_for_duty` on a synthetic curve recovers a known diameter;
- B-34004A: the diameter for rated duty lies within [125, 131] mm (assert the range, and record the value in the changelog).

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
- UC-07 ✅ in the registry.
- Changelog bullet; tracker ticked; one commit.

## Assumes
- Sprints 1–9 are done.
- The owner signs off on pure diameter affinity as the method. Mention that HI-style trim corrections are out of scope.
