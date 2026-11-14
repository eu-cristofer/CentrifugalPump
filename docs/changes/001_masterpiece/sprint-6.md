# Sprint 6 — UC-11 Mechanical run acceptance

## Goal
The mechanical running test is a first-class part of the FAT:
- a time-stamped log of Pint quantities;
- data-driven acceptance criteria;
- a stabilisation check;
- a verdict, trend plots and a report section;
- the B-34004A 4 h run is loaded as the reference.

## Files
- `docs/product/use-cases.md`: register **UC-11 Mechanical run acceptance** (actor: FAT witness; input: 15-min readings; output: verdict + trends).
- `pump/mechanical_run.py` (new):
  - `RunReading`: a time, plus a dict of `channel → Quantity`;
  - `MechanicalRunLog(readings)`, sorted and immutable;
  - `MechanicalRunCriteria`, loaded from `pump/standards/*.toml` under a `[mechanical_run]` table, with an overlay as in S5. Fields:
    - `min_duration`;
    - per-channel `max` (vibration velocity/displacement, bearing/oil temperature, …);
    - per-channel `stabilisation` (max change per interval over the last N intervals);
    - `source` and `verified`.
  - `MechanicalRunChecker(log, criteria) -> MechanicalRunResult`, with per-channel max, a stabilised flag, duration and an overall pass.
  - Seed criteria: none verified. Placeholders come from the reference notebook (`examples/pump_api610_performance 1.ipynb` ~:280-285: vibration overall ≤ 3.0 mm/s, filtered ≤ 2.0 mm/s in the POR), marked `verified = false`.
- `pumpflow/signals.py`: `MechanicalRunSet` (pump_tag, readings) and `MechanicalRunResult`.
- `pumpflow/nodes/mechanical_run.py` (new node `mechanical_run`, registered in `pumpflow/nodes/registry.py`):
  - log table with time plus user-defined channels, each with a unit header (re-use S3 `UnitColumnHeader` and `parse_unit_header` paste);
  - criteria editor;
  - verdict banner;
  - `compute` emits the set + result.
- `pumpflow/nodes/report_export.py` `_bundle`: accepts `MechanicalRunResult` on the `branch` port, keyed by pump_tag.
- `pumpflow/binding.py`: `check_mechanical_run(...)`; `assemble_report_data` adds `"Mechanical Run"` per tag (table + verdict + trend PNG).
- Reports: a "Mechanical running test" section in `pump/utilities/report.py` (docx) and `report_latex.py` (tex/pdf), with `.po` en/pt strings.
- `pump` plotting: `plot_mechanical_run(log) -> BytesIO`, one subplot per channel group, with limit lines.
- `examples/user/B-34004A_MRT_reference.pumpflow`: add a `mechanical_run` node for B-34004A, plus a blank B-34004B mechanical_run node.
  - Readings below are transcribed from `examples/user/mrt_performance.PDF` pp. 12–13 (Sundyne A&T Mechanical Run Data Sheet, 12/13/2011).
  - Pump speed is 10300 rpm.
  - Column units:
    - Flow [gpm], ΔP [psi], Power [kW] (electrical);
    - Vib filtered [in/s], Vib unfiltered [in/s];
    - Lube oil [psi g], Sump [°F], Seal cavity [psi g].

    | Time | Flow | ΔP | Power | Vib filt | Vib unfilt | Lube oil | Sump | Seal cavity |
    |---|---|---|---|---|---|---|---|---|
    | 06:00 | 43.53 | 487.32 | 29.72 | 0.04 | 0.15 | 44 | 116 | 69.34 |
    | 06:15 | 43.51 | 486.45 | 29.42 | 0.04 | 0.15 | 44 | 120 | 66.77 |
    | 06:30 | 43.51 | 484.71 | 29.08 | 0.04 | 0.15 | 42 | 121 | 65.89 |
    | 06:45 | 43.49 | 485.58 | 28.78 | 0.04 | 0.15 | 42 | 121 | 65.82 |
    | 07:00 | 43.49 | 485.58 | 28.71 | 0.04 | 0.16 | 42 | 122 | 66.11 |
    | 07:15 | 43.51 | 484.71 | 28.61 | 0.05 | 0.15 | 42 | 122 | 65.15 |
    | 07:30 | 43.47 | 485.58 | 28.76 | 0.05 | 0.15 | 42 | 122 | 65.38 |
    | 07:45 | 43.51 | 484.71 | 28.83 | 0.05 | 0.15 | 42 | 121 | 64.94 |
    | 08:00 | 43.49 | 485.58 | 28.86 | 0.05 | 0.14 | 42 | 120 | 65.16 |
    | 08:15 | 43.51 | 485.58 | 29.15 | 0.05 | 0.15 | 42 | 121 | 66.09 |
    | 08:30 | 43.49 | 486.59 | 29.11 | 0.05 | 0.15 | 42 | 121 | 65.45 |
    | 08:45 | 43.51 | 486.45 | 29.08 | 0.05 | 0.15 | 42 | 121 | 65.67 |
    | 09:00 | 43.51 | 486.45 | 29.03 | 0.05 | 0.16 | 42 | 122 | 65.89 |
    | 09:15 | 43.49 | 486.45 | 28.98 | 0.05 | 0.15 | 42 | 123 | 66.11 |
    | 09:30 | 43.49 | 487.32 | 29.03 | 0.05 | 0.15 | 42 | 122 | 65.67 |
    | 09:45 | 43.51 | 487.32 | 29.08 | 0.05 | 0.14 | 42 | 123 | 65.53 |
    | 10:00 | 43.49 | 487.32 | 29.11 | 0.05 | 0.14 | 42 | 124 | 65.65 |

## Reuse
- The S5 toml loader and overlay (`pump/acceptance.py`).
- S3 `UnitColumnHeader` and `parse_unit_header`.
- `ExploreChartNode` palette for consistent colours.
- `report_export._bundle` grouping by pump_tag.

## Tests
- `tests/test_mechanical_run.py` (Qt-free):
  - synthetic pass and fail logs (over the vibration limit, not stabilised, too short);
  - unit mixing (in/s vs mm/s) gives the same verdict;
  - B-34004A log → 17 readings, duration 4 h, max filtered vibration 0.05 in/s (1.27 mm/s);
  - sump temperature over the last hour (09:00–10:00) spans 122–124 °F, i.e. Δ ≤ 2 °F. The stabilisation rule in the test uses this value only as an example threshold, marked unverified.
- `tests/test_report_formats.py`: the section appears in docx and tex when present.
- Qt offscreen: the node evaluates; B blank → `invalid`, not `error`.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```
The PDF contains the mechanical-run section for B-34004A. Render a page with `gs` and inspect it.

## Definition of done
- UC-11 is registered and ✅ in the registry.
- Changelog bullet notes the criteria verification state.
- Tracker ticked; one commit.

## Assumes
- Sprints 1–5 are done; the `pump/standards` toml mechanism exists.
- **Owner input (optional):** confirmed vibration and stabilisation limits for an OH6 integrally geared pump (API 610 8th + N-553). Without it, ship `verified = false`.
