# Sprint S2 — Pin the MVP physics (8 h)

- **Goal:** Regression-lock the two physics behaviours the FAT engineer relies on:
  API 610 compliance bands and affinity-law speed correction.
- **Persona / UC:** FAT engineer · UC-02 (verify performance), UC-06 (speed change).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [x] Write [`tests/test_compliance.py`](../../tests/test_compliance.py) — pin
  `PerformanceChecker` head band (±3 %), power ceiling (+4 %), and the three shutoff
  tiers (≤75→10 %, ≤300→8 %, >300→5 %)
  ([`performance_curve.py:637-668`](../../pump/performance_curve.py#L637-L668)); assert
  `report_summary` / `acceptable_limits` keys & rated-point values — ~4.5h
- [x] Write [`tests/test_affinity.py`](../../tests/test_affinity.py) — `to_speed`
  Q/H/P scaling laws + round-trip `to_speed(N).to_speed(N0)` within `< 1e-6`
  ([`performance_curve.py:435`](../../pump/performance_curve.py#L435)) — ~2.5h
- [x] Run suite (**34 passed**) — ~1h

> **Note:** pinned against the conftest reference curve (deterministic, no fitted-number
> drift) rather than the example notebooks' fitted coefficients — the tiers and bands
> are the API 610 spec values, which is what UC-02/UC-06 acceptance actually requires.

## Files touched

- Create: `tests/test_compliance.py`, `tests/test_affinity.py`.

## Acceptance criteria

- Compliance bands and shutoff tiers match a worked example within tolerance.
- UC-06 round-trip acceptance criterion (`< 1e-6`) holds in the test.
- `pytest -v` green.

## Definition of Done

- [x] Both behaviours regression-locked (34 passed total); committed.
