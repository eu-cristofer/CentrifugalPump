# Sprint 5 — Edition-aware acceptance engine

## Goal
Performance acceptance is driven by **data tables per standard and edition**, with a client overlay, instead of the hard-coded ±3 % / +4 %:
- the GUI and the library compute limits the same way;
- open review findings are fixed;
- the report cites the edition actually selected.

## Files
- `pump/standards/` (new package data):
  - `api610.toml`: one table per edition, `8`, `10`, `11` and `12`;
  - `iso9906.toml`: grades `1B`, `2B`;
  - `clients/n553.toml`: overlay layer.
  - Each row:
    - `rated_head_bands` = list of `{max_head = Q, tol_minus, tol_plus}`;
    - `shutoff_bands` (same shape);
    - `power_tol_plus`;
    - `efficiency_tol_minus`;
    - `npsh` (placeholder for S8);
    - `source` (string: clause/table reference);
    - `verified` (bool).
  - **Seed rule:** only the values already in the code are seeded, each marked `verified = false`:
    - head ±3 %;
    - power +4 %;
    - shut-off 10/8/5 % keyed ≤75 / ≤300 / >300 m;
    - efficiency −3 % (GUI).
  - **Do not invent edition-specific numbers.** The owner fills or confirms them; see Assumes.
- `pump/acceptance.py` (new):
  - `AcceptanceCriteria.load(standard, edition, client=None)`, with overlay merge;
  - `limits_for(design_point) -> dict`, with bands keyed by **rated differential head** for the head and by the **rated head** for shut-off, as the library does today. Document the key choice in a docstring.
  - Uses stdlib `tomllib` (the project floor is Python 3.12). Declare the package data in `pyproject.toml` (`pump = [..., "standards/**/*.toml"]`).
- `pump/performance_curve.py` `PerformanceChecker`:
  - takes an `AcceptanceCriteria`; the default is today's behaviour, so old call sites still work;
  - **F-01:** `acceptable_limits` must not crash when shut-off or power data is missing; omit those rows instead;
  - **F-02:** `check_summary` must not apply the rated ±band to every raw test point;
  - honour the currently ignored `acceptable_limits` constructor argument, or remove it with a deprecation warning;
  - one deviation formula, `(predicted − rated)/rated`, shared with the GUI (**F-05**);
  - extrapolated shut-off is flagged when no test point has Q < 5 % of rated (**F-07**);
  - parallel-operation check: if `parallel_operation`, the rising-curve rule is shut-off head ≥ 110 % of rated head. Mark it `verified = false` in toml with its source as "reference notebook".
- `pumpflow/binding.py`:
  - `default_tolerances` and `check_compliance` delegate entirely to `pump.acceptance` and `PerformanceChecker`, with no parallel tolerance logic left;
  - `ParameterCheck` gains `extrapolated: bool` and `verified: bool`.
- `pumpflow/signals.py` `RatedPoint`: add `standard_key: str` (e.g. `"api610:8"`) and `client: str | None`, keeping `standard` as the display label.
  - Migration: parse the free text if possible (`"API 610 8th"` → `api610:8`, `N-553` → client `n553`); otherwise the default is `api610:12`.
- `pumpflow/nodes/rated_point.py`: a standard/edition combo and a client overlay combo.
- `pumpflow/nodes/compliance.py`:
  - shows the band source and an **"unverified"** badge per row;
  - user overrides stay.
- Reports, `pump/utilities/report.py` and `report_latex.py`:
  - `TEST_SUMMARY_DESCRIPTION` takes the edition from the criteria instead of the hard-coded "API 610 12th issue";
  - add `.po` strings in en and pt;
  - add a "Deviations / unverified criteria" note when any used row is unverified.

## Reuse
- `PerformanceChecker._get_shutoff_tolerance` (`pump/performance_curve.py:669-683`): its logic moves to toml.
- `binding.default_tolerances` (`:389`) and `check_compliance` (`:401`).
- `tests/test_compliance.py` expectations.

## Tests
- `tests/test_acceptance.py`:
  - each toml file loads; schema validated (bands sorted, tolerances ≥ 0);
  - the overlay replaces only the keys it defines;
  - the default criteria reproduce the `tests/test_compliance.py` results exactly;
  - F-01 regression (no shut-off data → no crash), F-02 regression, extrapolation flag, parallel-operation rule.
- GUI and library limits are identical for the B-34004A rated point.
- `tests/test_report_formats.py`: the edition string appears in tex/docx.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```
- B-34004A is set to `api610:8` with client `n553`.
- Its verdict depends on the confirmed head band. Report the head deviation, about +1.7 %, against the band in use, in the changelog.

## Definition of done
- No tolerance number is hard-coded outside `pump/standards/*.toml`.
- Changelog bullet lists which rows are verified.
- Tracker ticked; one commit.

## Assumes
- Sprints 1–4 are done.
- **Owner input:** before running, the owner provides confirmed API 610 8th edition and N-553 tolerance values (head bands for >300 m, power, efficiency, shut-off). If they are not provided, ship seeds as `verified = false` and note `BLOCKED-PARTIAL: tolerance values unverified` under the tracker line (not a stop condition).
