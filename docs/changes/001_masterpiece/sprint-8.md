# Sprint 8 — UC-05 NPSH margin

## Goal
NPSH becomes real physics:
- NPSHa computed from suction conditions;
- NPSHr from a 3 % head-drop test;
- a margin check against the selected criteria;
- shown in the GUI and in the report.

## Files
- `pump/npsh.py` (new):
  - `npsh_available(p_suction: Pressure, fluid, temperature, q, suction_id=None, suction_elevation_to_datum=0 m) -> Quantity`:
    - NPSHa = (p_s,abs − p_v)/(ρg) + v_s²/(2g) + z_s;
    - p_v comes from `Water.vapour_pressure(T)` (S1) or from a fluid that supplies `vapour_pressure`;
    - `Fluid` gains an optional `vapour_pressure` attribute.
  - `NPSHTest(points)`, where each point is (Q, NPSHa, head at that NPSHa):
    - `npsh3()` finds the NPSHa where head has dropped 3 % from the non-cavitating head at each flow, by linear interpolation;
    - returns a `Quantity` per Q;
    - `npshr_curve(degree=2)` fits a polynomial.
  - `npsh_margin(npsha, npshr) -> {"ratio", "margin"}`.
- `pump/standards/*.toml`: `[npsh]` criteria (`min_ratio`, `min_margin`), `verified = false` unless confirmed (N-553 / API 610 edition).
- `pump/acceptance.py`: expose the NPSH criteria (S5 loader).
- Naming fix: notebooks use `NPSH_available` while the GUI and `DesignPoint` use `npsha`. Standardise on `npsha` in the library: `DesignPoint` accepts `NPSH_available` as a deprecated alias with a `DeprecationWarning`. Update `examples/P-9006D.ipynb` and `examples/Example_2.ipynb` call sites (code cells only).
- `pumpflow/signals.py`: `NPSHTestSet` and `NPSHResult`.
- `pumpflow/nodes/npsh.py` (new node `npsh`, registered):
  - mode A, "NPSHa calculator": suction pressure (with g/a), temperature, fluid, Q, geometry;
  - mode B, "NPSH 3 % test": a table with per-column units;
  - outputs NPSHa, NPSHr at rated, the margin verdict and a plot.
- `pumpflow/binding.py`: `assemble_report_data` adds an "NPSH" entry per tag when present.
- Reports: an NPSH section in docx/tex (table + plot + verdict); `.po` en/pt.
- `pumpflow/nodes/rated_point.py`: NPSHa stays as a datasheet value. The NPSH node can override it when wired.
- P-9001A: add an NPSH node with datasheet NPSHa 2.4 m and the test's design-point NPSHr.
  - Vendor A p.1 gives TNPSHR = 4.06 ft = 1.24 m at design (p.2 per-point NPSHR: 2.7, 2.9, 3.3, 4.1, 3.3 ft at 15.2, 29.4, 34.8, 43.5, 47.9 gpm).
  - Enter the per-point NPSHR as a direct NPSHr curve. Mode B supports "direct NPSHr points" as well as raw 3 % data.

## Reuse
- `Pressure`, `G`, `Water.vapour_pressure` (S1); `TestPoint.velocity_head` (`pump/point.py:348`).
- S5 criteria loader; S3 `UnitColumnHeader`.
- `RatedPoint.npsha` (already wired: `signals.py`, `rated_point.py`, `binding.make_design_point`).

## Tests
- `tests/test_npsh.py`:
  - NPSHa hand calculation: water 20 °C, p_s = 1.2 bar a, Q = 50 m³/h, ID 100 mm, z = 0;
  - 3 % detection on a synthetic head-vs-NPSHa sweep with a known knee;
  - ratio and margin;
  - `NPSH_available` alias warns.
- P-9001A: margin at rated is 2.4 / 1.24 ≈ 1.94; the verdict follows the configured criteria.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/p9001 --formats docx,tex,pdf
```

## Definition of done
- UC-05 ✅ in the registry.
- Changelog bullet (criteria verification state); tracker ticked; one commit.

## Assumes
- Sprints 1–7 are done.
- **Owner sign-off** on the NPSH margin rule to apply (ratio and/or absolute margin; N-553 value). Without it, ship `verified = false`.
