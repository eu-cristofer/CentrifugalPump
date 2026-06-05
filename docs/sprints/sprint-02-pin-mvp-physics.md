# Sprint S2 — Pin the MVP physics (8 h)

- **Goal:** Regression-lock the two physics behaviours the FAT engineer relies on:
  API 610 compliance bands and affinity-law speed correction.
- **Persona / UC:** FAT engineer · UC-02 (verify performance), UC-06 (speed change).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [ ] Write [`tests/test_compliance.py`](../../tests/test_compliance.py) — pin
  `PerformanceChecker` tolerance bands (±3 % head, +4 % power) and shutoff tiers
  ([`performance_curve.py:637-668`](../../pump/performance_curve.py#L637-L668)) against
  numbers from [`examples/B-432301D.ipynb`](../../examples/B-432301D.ipynb) /
  [`examples/52-P-11AB.ipynb`](../../examples/52-P-11AB.ipynb); assert `report_summary`
  keys & values — ~4.5h
- [ ] Write [`tests/test_affinity.py`](../../tests/test_affinity.py) — `to_speed`
  scaling laws + round-trip `to_speed(N).to_speed(N0)` within `< 1e-6`
  ([`performance_curve.py:435`](../../pump/performance_curve.py#L435)) — ~2.5h
- [ ] Run suite; reconcile any example-number drift — ~1h

## Files touched

- Create: `tests/test_compliance.py`, `tests/test_affinity.py`.

## Acceptance criteria

- Compliance bands and shutoff tiers match a worked example within tolerance.
- UC-06 round-trip acceptance criterion (`< 1e-6`) holds in the test.
- `pytest -v` green.

## Definition of Done

- [ ] Both behaviours regression-locked; committed.
