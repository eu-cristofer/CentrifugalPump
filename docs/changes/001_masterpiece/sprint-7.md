# Sprint 7 — UC-08 Compare pumps (twin A vs B)

## Goal
Two or more tested units, such as twin B-34004A vs B-34004B, are compared:
- in the library: an overlay plot plus a delta table at rated Q and user-chosen Q's;
- in the GUI;
- in a "Comparison" report section whenever a report has ≥ 2 branches.

## Files
- `pump/compare.py` (new):
  - `compare_curves(curves: dict[str, PerformanceCurve], at: list[Quantity]) -> ComparisonTable`, with H, P, η per curve and deltas against the first curve (absolute and %);
  - `plot_comparison(curves, rated=None) -> BytesIO`, with H/P/η stacked subplots in a consistent palette.
  - This replaces the broken notebook draft `PumpSystem.compare_curves` (`examples/Example_1.ipynb` ~:791-842: NameError `plt`, nonexistent `_get_capacities`). Leave the notebook untouched apart from a markdown cell pointing to `pump.compare`.
- `pumpflow/binding.py`:
  - `comparison_for(bundles, rated)`;
  - `assemble_report_data` adds a top-level `"comparison"` entry when ≥ 2 fitted branches exist.
- Reports (`report.py`, `report_latex.py`): a "Comparison" section with the table and overlay figure; `.po` strings en/pt.
- `pumpflow/nodes/explore_plot.py`: a delta column in the readout table against the first model.
- `pumpflow/nodes/compare.py` (new optional node `compare`):
  - multi-input FittedModel, plus RatedPoint;
  - shows the table and figure;
  - registered in `registry.py`.

## Reuse
- `PerformanceCurve.predict_head` / `predict_breaking_power` / `predict_efficiency` (`pump/performance_curve.py:220-260`).
- `plot_performance_curve` styling (`:282`).
- The `ExploreChartNode` multi-model readout (`pumpflow/nodes/explore_plot.py:233-283`) and `_PALETTE` (`:33`).

## Tests
- `tests/test_compare.py`:
  - two synthetic curves with known H offset → table deltas exact;
  - the figure is a PNG.
- Report: with the sample A/B fixture (build two branches from `tests/conftest.py` curves), both docx and tex contain "Comparison" and both tags.
- B-34004A + a synthetic filled B: the comparison section renders. The test builds B in memory; do not commit fake B data to the project file.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```
With only branch A filled, no comparison section appears and nothing crashes.

## Definition of done
- UC-08 ✅ in the registry.
- Changelog bullet added; tracker ticked; one commit.

## Assumes
Sprints 1–6 are done; `report_data` carries per-tag entries plus optional mechanical run.
