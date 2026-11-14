# Sprint 12 — UC-01 Pump selection

## Goal
Given a duty (Q, H, fluid), rank candidate pumps from a catalogue of known curves:
- each candidate is adapted by speed (VFD) and/or diameter (trim);
- candidates are scored on efficiency at duty, position relative to BEP (preferred/allowable operating region), and the remaining trim margin.

## Files
- `pump/catalogue.py` (new):
  - `CatalogueEntry(name, curve: PerformanceCurve, speed, diameter, d_min, d_max, speed_range=None)`;
  - `Catalogue.from_folder(path)`: loads `*.pumpcurve.json` files, a curve format defined here (test points as `{"value","unit"}` pairs via `pump.quantity_io`, plus fluid, speed and impeller diameters).
    - **`pump` must never import `pumpflow`** (layering).
    - The `.pumpflow` → `.pumpcurve.json` conversion lives in pumpflow: `pumpflow/binding.py` `export_pumpcurve(fitted, rated, path)`, plus an "Export curve to catalogue" button on the Report Export or Curve Fit node.
  - `select(duty_q, duty_h, fluid, allow_speed=True, allow_trim=True) -> list[Candidate]`:
    - each candidate is adapted using `to_speed` (existing) or `to_diameter` (S10) to pass through the duty, via the affinity-parabola solve from `pump/trim.py`;
    - score fields: η at duty; Q/Q_BEP ratio; in-POR flag (POR bounds in `pump/standards` toml, `verified = false` seed 70–120 % of BEP); trim margin;
    - deterministic ordering.
- `pumpflow/nodes/selection.py` (new node `selection`):
  - duty inputs as `UnitField`s plus a catalogue folder picker;
  - a ranked table;
  - "Send to canvas" adds a Rated Point plus Plot pre-filled for the chosen candidate;
  - registered in `registry.py`.
- `examples/catalogue/`: 3–4 curve JSON files derived from the shipped examples (sample_project, B-2351105, B-34004A), so the feature works out of the box.

## Reuse
- `PerformanceCurve.to_speed`, `to_diameter` (S10), `bep()` (S9), `pump/trim.py` `diameter_for_duty` (S10).
- `pump.quantity_io` (S1) for the JSON format.
- The S5 toml loader for POR bounds.

## Tests
`tests/test_selection.py`:
- a synthetic 3-pump catalogue with known BEPs: the ranking is deterministic and the expected pump wins;
- an out-of-range duty (no candidate) returns an empty list with reasons;
- a units-mixed duty (gpm/ft) gives the same ranking;
- `Catalogue.from_folder(examples/catalogue)` loads all entries.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
- UC-01 ✅ in the registry.
- Changelog bullet; tracker ticked; one commit.

## Assumes
- Sprints 1–11 are done: `to_diameter`, `diameter_for_duty`, `bep()`, toml criteria.
- Owner sign-off on the POR bounds (seeded 70–120 % of BEP, unverified).
