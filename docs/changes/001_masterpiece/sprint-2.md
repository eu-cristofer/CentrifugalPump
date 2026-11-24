# Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2

## Goal
- Every payload that flows along a link carries `pint.Quantity` values instead of floats with implied units.
- `binding.py` contains no hard-coded unit assumptions.
- `.pumpflow` files are written in **schema v2**: every numeric setting is `{"value", "unit"}`.
- A migrator upgrades any v1 file losslessly on load.

## Files
- `pumpflow/signals.py`: rename and retype the fields.
  - `RatedPoint`: `q`, `head`, `speed`, `power`, `efficiency`, `head_shutoff`, `npsha`, `density`, `viscosity` (Quantities; `density` replaces `density_rel`, keeping a `density_rel` property).
  - `FluidSpec`: `density`, `viscosity`, `temperature`.
  - `TestRow`: `q`, `p_suction: Pressure`, `p_discharge: Pressure`, `temperature`, `speed`, `power`, plus optional `head` and `efficiency`.
  - `TestPointSet`: drop `pressure_unit`; `test_density` becomes a Quantity or None.
  - `PointSample`: the same treatment.
  - Keep `@dataclass(frozen=True)` and update `is_valid()` checks to compare quantities.
  - Update every consumer: `pumpflow/nodes/*.py`, `pumpflow/nodes/plotting.py`, `report_export._bundle_json`, `sample_data.py`, `persistence.rated_from_json/testset_from_json/json_from_signals`.
- `pumpflow/binding.py`:
  - delete `_PA_PER` and `pressure_to_pa`;
  - `row_head_m` becomes `row_head(row, density) -> Quantity`, computed as `((p_dis - p_suc) / (rho * G)).to("m")` using `pump.utilities.pressure.Pressure`;
  - `row_efficiency` uses Pint arithmetic;
  - remove every literal `Q_(x, "m**3/h")`-style re-wrap of signal fields;
  - output conversions use `quantity_factory`.
- `pumpflow/persistence.py`:
  - `SCHEMA_VERSION = 2`;
  - `migrate(doc) -> doc`, a pure function with no Qt;
  - `read_json` calls `migrate` for project files.
  - v1 → v2 rules:
    - rated `q`/`q_unit` → `{"value","unit"}`; a missing `*_unit` takes the **canonical** unit (m³/h, m, kW, cSt), never the active preset, which fixes the audit hazard;
    - rated `n`→rpm, `eff`→%, `head_shutoff`→m, `npsha`→m;
    - drop the stale `rated.unit`;
    - test_points: node `unit` ("bar" or "kgf/cm**2", gauge) becomes the pressure columns' unit; rows become per-column magnitudes plus a `columns: {"q": "m³/h", "p_suc": "bar g", …}` header;
    - correction `target_speed`→rpm;
    - fluid `temp`/`dens`/`visc` are already unit-paired → `{"value","unit"}`.
- `pumpflow/canvas/scene.py`:
  - `to_dict` writes `meta.schema_version = 2`;
  - `load_dict` runs `persistence.migrate` first.
- Node `default_settings` and `serialize_settings` emit v2 shapes. Settings may hold Quantities at runtime but must serialise through `pump.quantity_io.to_json`.
- `pumpflow/sample_data.py` and the shipped examples:
  - regenerate `examples/sample_project.pumpflow` and `pumpflow/examples/*.pumpflow` in v2;
  - **do not overwrite** `examples/user/*` except `P-9001A_MRT_reference.pumpflow`, which is re-saved through the scene in v2.

## Reuse
- `pump.quantity_io.to_json/from_json`, `pump.utilities.pressure.Pressure` and `pump.constants.G` (Sprint 1).
- `quantity_factory`.
- `pumpflow/units.py` `_pint_str` mapping display labels to Pint strings, for converting label units found in v1 files.

## Tests
- `tests/test_schema_migration.py` (Qt-free):
  - for **every** `.pumpflow` under `examples/`, `examples/user/` and `pumpflow/examples/`, take the v1 doc (from `git show 2e1983a:<path>` captured as fixtures in `tests/fixtures/v1/`), then `migrate`, then rebuild signals;
  - predicted H/P/η at rated Q and the verdict must be **identical** (rel 1e-9) to the v1 pipeline results captured as fixture JSON;
  - `migrate(migrate(doc)) == migrate(doc)` (idempotent).
- `tests/test_persistence_roundtrip.py`:
  - update for v2;
  - the scene round-trip is a fixed point;
  - P-9001A A branch is APPROVED with unchanged numbers.
- `tests/test_report_formats.py` still passes. The `report_data` contract is unchanged; build it via the new signals.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/p9001 --formats docx,tex,pdf
grep -n "_PA_PER\|pressure_to_pa\|q_m3h\|speed_rpm\|power_kw" -r pumpflow pump | grep -v "^docs" ; test $? -eq 1
```

## Definition of done
- No implied-unit float fields remain in `signals.py`.
- `binding.py` has no unit literals for signal fields.
- All shipped projects load, migrate and produce identical verdicts.
- Changelog bullet: "`.pumpflow` schema v2 (value+unit); old files migrate automatically on open".
- Tracker ticked; one commit.
- If this sprint overruns, split it: "2a binding/persistence" and "2b nodes". Note the split under the tracker line and stop after 2a with the suite green.

## Assumes
Sprint 1 is done: `pump.quantity_io`, `pump.utilities.pressure.Pressure`, `pump.constants.G` and `STANDARD_UNITS["kinematic_viscosity"]` exist.
