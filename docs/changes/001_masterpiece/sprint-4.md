# Sprint 4 — Complete head (pressure + velocity + elevation)

## Goal
Measured total head follows the full definition used by API 610 / ISO 9906:

H = (p_d − p_s)/(ρg) + (v_d² − v_s²)/(2g) + (z_d − z_s)

Pipe IDs and gauge elevations are optional per test set. Without geometry the result is identical to today's ΔP-only head.

## Files
- `pumpflow/signals.py`: `TestPointSet` gains optional Quantities `suction_id`, `discharge_id`, `suction_gauge_elevation`, `discharge_gauge_elevation`. They are per set, since the bench is fixed for the whole test.
- `pumpflow/nodes/test_points.py`: a "Test bench geometry" group in the dialog with four `UnitField`s (length), persisted as v2 values.
- `pumpflow/binding.py`:
  - `correct_curve` and the per-row head build `pump.TestPoint` with `inlet_pressure`/`outlet_pressure` (or `delta_pressure`), `inlet_diameter`/`outlet_diameter` and `inlet_elevation`/`outlet_elevation`;
  - head comes from `TestPoint.compute_head` (`pump/point.py:414-427`) instead of a precomputed `_head` whenever geometry is given;
  - an explicit row head override still wins.
- `pump/point.py`:
  - verify `velocity_head` (`:348-397`) and `elevation_head` (`:399-410`) use `G` from `pump.constants`, and handle a missing diameter as zero velocity head without raising;
  - fix any attribute-name/context pitfalls: `extract_context` must not misroute `inlet_*`/`outlet_*`.
- Report:
  - `assemble_report_data` adds the geometry to the equipment/test description when present;
  - the Test Points table's derived Head tooltip shows the three components.

## Reuse
- `TestPoint.pressure_head`, `velocity_head`, `elevation_head` and `compute_head` (`pump/point.py:316-427`).
- `DesignPoint` velocity helpers (`:164-212`) as a reference.
- `Pressure` (S1).

## Tests
- `tests/test_head_components.py` (Qt-free), hand calculation:
  - Q = 100 m³/h, p_s = 1 bar g, p_d = 6 bar g, ρ = 998 kg/m³;
  - suction ID 150 mm, discharge ID 100 mm;
  - z_s = 0.3 m, z_d = 0.8 m;
  - compute each component by hand in the test (written formulas, Pint) and assert `binding` head == sum (rel 1e-9).
- No geometry → identical to the ΔP-only head of Sprint 3 (rel 1e-12).
- B-34004A has no geometry, so its results are unchanged.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
- Geometry is persisted (v2) and migrated as absent for older files.
- The report shows it when present.
- Changelog bullet added; tracker ticked; one commit.

## Assumes
Sprints 1–3 are done: `Pressure`, `G`, Quantity signals and per-column units exist.
