# Sprint 3 — Unit choice on every GUI numeric field

## Goal
The engineer types every number in whatever unit the instrument or vendor sheet uses:
- gpm, psi g/a, °F, hp, rpm, in/s, mm, ft, …
- one unit per column in the Test Points table;
- changing a unit **converts** the stored values, not just the label.

As a showcase, B-34004A is re-entered in the vendor's native units with no hand conversion and gives identical results.

## Files
- `pumpflow/units.py`:
  - `UNIT_OPTIONS` gains these dimensions, canonical unit first:
    - `pressure`: bar, kgf/cm², psi, kPa, MPa, mH₂O. The gauge/absolute reference is a separate toggle stored with the value, e.g. `"unit": "psi", "ref": "g"`.
    - `speed`: rpm, Hz.
    - `length`: mm, in, m.
    - `npsh`: m, ft.
    - `efficiency`: %, fraction.
    - `vibration_velocity`: mm/s, in/s.
    - `vibration_displacement`: µm, mil.
  - Extend `PRESETS` SI/US accordingly.
  - Add `parse_unit_header("Q [gpm]") -> (key, unit, ref)`.
- `pumpflow/nodes/ui.py`:
  - `UnitField` supports `pressure` with a g/a toggle and the new dimensions;
  - new `UnitColumnHeader` helper: a combo per table column.
- `pumpflow/nodes/test_points.py`:
  - per-column unit combos for Q, P_suc, P_dis (with g/a), T, N and P;
  - read-only Head and η columns get display units too;
  - on unit change, convert all stored magnitudes of that column through `units.convert_display`;
  - paste parses an optional header row through `parse_unit_header`;
  - remove the node-level pressure-unit combo, now superseded per column;
  - remove the duplicate `TestRow` construction (`to_signal` and `refresh_computed`) by using one helper.
- `pumpflow/nodes/rated_point.py`: `UnitField` for `n`, `eff`, `head_shutoff`, `npsha`, and for density as a real magnitude, not only `dens_rel`.
- `pumpflow/nodes/point.py`: pressures via `UnitField` (`pressure`); remove the private bar/kgf combo.
- `pumpflow/nodes/correction.py`: `target_speed` via `UnitField("speed")`.
- `pumpflow/nodes/performance_plot.py`: optional y-limit `UnitField`s in the dialog. Today the settings exist but nothing edits them.
- `pumpflow/nodes/explore_plot.py`: the readout Q `UnitField`; axis labels follow the preset.
- `pumpflow/app.py`: the Units menu presets include the new dimensions.
- `examples/user/B-34004A_MRT_reference.pumpflow`: re-enter test_a rows in native units.
  - Columns: Q [gpm], P_suc [psi g] = 0, P_dis [psi g] = ΔP, T [°F], N [rpm] (pump shaft), P [hp] (motor output).
  - Rows, in the order Q / ΔP / T / P:

    | Q (gpm) | ΔP (psi) | T (°F) | P (hp) |
    |---|---|---|---|
    | 15.2 | 524.7 | 130 | 25.41 |
    | 29.4 | 522.1 | 129 | 28.83 |
    | 34.8 | 513.4 | 129 | 30.56 |
    | 43.5 | 486.5 | 127 | 33.36 |
    | 47.9 | 459.5 | 126 | 35.09 |
    | 52.2 | 431.7 | 126 | 36.61 |

  - N = 10301 rpm on every row.
  - Update the canvas note's "Data entry conventions" section: no manual conversion any more.

## Reuse
- `UnitField`, `units.convert_display`, `units.to_standard`, `PREFS` (`pumpflow/units.py`, `pumpflow/nodes/ui.py`).
- `Pressure` (S1); v2 settings shapes (S2).

## Tests
- `tests/test_units_gui.py` (Qt offscreen, skipped without PySide6):
  - switching the Test Points Q column m³/h → gpm → m³/h leaves the computed Head column unchanged (rel 1e-9) and the stored magnitudes converted;
  - the same for pressure bar → psi.
- `tests/test_units.py` (Qt-free):
  - `parse_unit_header` cases: `"Q [gpm]"`, `"P_dis [psi g]"`, `"P_suc [bar a]"`, `"T [°F]"`, unknown unit → `ValueError`;
  - every `UNIT_OPTIONS` entry resolves in Pint.
- B-34004A regression: predicted H/P/η equal to the S2 values within 0.05 %. The residual comes only from rounding of the previously hand-converted inputs. Record the values.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```
Manual check: `python -m pumpflow`, open B-34004A, switch a column unit and observe the values convert.

## Definition of done
- `grep -n "ui.spin(" pumpflow/nodes/*.py` shows no spin box for a dimensional quantity. Remaining spins are counts or degrees only.
- Changelog bullet added; tracker ticked; one commit.

## Assumes
Sprint 2 is done: signals carry Quantities, settings are v2 `{"value","unit"}`, and `persistence.migrate` exists.
