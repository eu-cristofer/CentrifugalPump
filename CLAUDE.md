# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

`centrifugal-pump` is a Python library for assessing API 610 centrifugal pumps during Performance and Mechanical Running Test (FAT) trials. It computes hydraulic quantities, fits polynomials to measured test points, checks results against API 610 tolerances, and generates Word-document (`.docx`) acceptance reports.

## Common commands

```bash
# Editable install with dev tools (black, build, pytest)
pip install -e .[dev]

# Or use the conda env (Python 3.12 + Jupyter + plotly + xlrd, then pip-installs the package editable)
mamba env create -f environment.yml
mamba activate pump
mamba env update -f environment.yml   # after editing environment.yml

# Build sdist + wheel into dist/
python -m build

# Tests — pytest is declared as a dev dep but no test files exist yet.
# tests/ currently holds only Jupyter notebooks (utilities_test.ipynb, pip_test.ipynb).
# The README TODO explicitly lists "Add testing" as outstanding work.
pytest                            # discover & run (currently a no-op)
pytest tests/path::test_name      # run a single test once tests are added

# Formatting
black .
```

There is no lint or type-check configured. The README TODO lists "Check style guidelines" and "Run type checking" as outstanding.

## Architecture

### The units spine: everything flows through `quantity_factory`

The library is built around Pint quantities normalized to a fixed table of standard units. `pump/utilities/unit_conversion.py` defines:

- `STANDARD_UNITS` — dimensionality → standard-unit map (capacity → `m**3/h`, pressure → `kgf/cm**2`, power → `kW`, etc.), with per-context overrides (`pressure` has `default`, `atm`, `delta`).
- `quantity_factory(q, context="default")` — the single entry point for unit normalization. It dispatches by `q.dimensionality` to find the matching `STANDARD_UNITS` row, then converts to the unit for the given context.
- `extract_context(key)` — when attributes are set dynamically via `**kwargs`, the attribute name is split on `_`; if the first token is a known context (`atm`, `delta`, `default`), that context is used for conversion. **This means attribute naming directly controls unit handling** — e.g., `inlet_pressure=Q_(1, "atm")` is converted via the `atm` context (→ pascal) because `inlet` is not a context, while `atm_pressure=Q_(1, "atm")` would route through the `atm` context for a different reason. Be careful when adding kwargs whose first token happens to match a `CONTEXT` value.

Any new physical quantity added to a `Fluid`, `BasePoint`, or any subclass should be a `Q_`; non-`Quantity` values raise `ValueError` at construction. To add a new dimensionality (e.g., viscosity correction — listed in README TODO), extend `STANDARD_UNITS` rather than calling `.to()` ad-hoc.

### Domain model: `Fluid` + the `BasePoint` hierarchy

[pump/utilities/fluid.py](pump/utilities/fluid.py) defines `Fluid(name, density, **kwargs)`. Extra kwargs become attributes (viscosity, vapor pressure, etc.), each normalized via `quantity_factory`.

[pump/point.py](pump/point.py) defines:

- `BasePoint(fluid, capacity, **kwargs)` — generic point. Dynamic kwargs become Pint attributes.
- `DesignPoint(BasePoint)` — adds `differential_head` plus derived properties: `specific_energy`, `power_output` (hydraulic), `outlet_pressure`, `elevation_head`, `inlet_velocity`/`outlet_velocity`, `velocity_head`. Properties degrade gracefully — e.g., `elevation_head` returns 0 m if `inlet_elevation`/`outlet_elevation` aren't set.
- `Point(BasePoint)` — generic computed point. **Note: `Point.outlet_pressure` is a stub that calls `quantity_factory()` with no args and will fail.** It is essentially dead code.
- `TestPoint(BasePoint)` — measured-data point. Adds `pressure_head`, `velocity_head`, `elevation_head`, `compute_head`/`head` (cached as `_head`), `compute_hydraulic_power`/`hydraulic_power`, and `compute_efficiency`/`efficiency` (requires `breaking_power`). Sortable by capacity via `__lt__`.

Each `compute_*` property caches its result on a leading-underscore attribute (e.g. `_head`, `_efficiency`); the corresponding non-underscored property reads the cache if present, otherwise triggers the compute. When constructing a derived `TestPoint` (e.g. inside `PerformanceCurve.to_speed`), pass the cached value via `_head=...`/`_efficiency=...` so the new point keeps the original measurement rather than recomputing from pressures/diameters that may not be present.

### `PerformanceCurve` + `PerformanceFitter`

[pump/performance_curve.py](pump/performance_curve.py):

- `PerformanceFitter(points, polynomial_degree=4)` — lazy numpy polynomial fits for head/efficiency/power vs capacity. All arrays and coefficients are computed on first access and cached.
- `PerformanceCurve(fluid, points, polynomial_degree=4)` — owns a fitter and a sorted list of `TestPoint`s that **must all share the same `Fluid`** (enforced in `__init__`). Provides:
  - `predict_head`/`predict_efficiency`/`predict_breaking_power(capacity)` — evaluate the fits.
  - `plot_performance_curve(...)` — three-panel matplotlib chart (Head / Power / Efficiency), optionally returning a `BytesIO` PNG for embedding in reports.
  - `to_speed(new_speed)` — returns a **new** curve scaled via simplified affinity laws: capacity ∝ N, head ∝ N², power ∝ N³.
  - `to_fluid(new_fluid)` — returns a **new** curve with the same hydraulic head but `breaking_power` recomputed for the new density (assumes efficiency is invariant under fluid change).
  - `test_summary` / `test_data` — tabulated + dict views for reporting.

These transformations always return new instances; the original points are never mutated.

- `PerformanceChecker(design_point, performance_curve)` — applies API 610 tolerances:
  - head: ±3%
  - shutoff head: ±10% / ±8% / ±5% depending on differential head (≤75 m / ≤300 m / >300 m)
  - breaking power: +4%

  `check_summary`, `test_summary_with_limits`, and `report_summary` produce the artefacts consumed by `ReportGenerator`.

### Report generation

[pump/utilities/report.py](pump/utilities/report.py) generates `.docx` reports from `pump/templates/template_{en,pt}.docx` via `python-docx`. Localization uses gettext catalogs under [pump/utilities/locales/](pump/utilities/locales/) (`en`, `pt`). The `pt` catalog has a compiled `.mo`; `en` does not — strings without `.mo` fall back to the source English text.

`ReportGenerator(language='en')` walks a `report_data` dict with the keys `equipment_description`, `design_point`, and `test_data` (a dict of tag → per-test dicts containing `test_summary`, `test_data`, and any keys containing the substring `"Curve"`, which are treated as chart images — file paths or `BytesIO`). Output filename defaults to `{Report}_{TAG}_{DD-MM-YYYY}.docx`.

When changing template structure, update both `template_en.docx` and `template_pt.docx`, and add new translatable strings to both `.po` files under `pump/utilities/locales/*/LC_MESSAGES/messages.po`. Compile `pt` with `msgfmt messages.po -o messages.mo`.

## Conventions and gotchas

- **Always pass `Q_` (Pint quantities), never raw numbers.** `quantity_factory` rejects non-`Quantity` input.
- **Attribute naming controls unit conversion.** Prefixes that match `CONTEXT` (`atm`, `delta`, `default`) are interpreted as conversion contexts via `extract_context`. Prefer descriptive prefixes that aren't context names (`inlet_…`, `outlet_…`) unless context-routing is intentional.
- **Property caches use leading underscores.** When building derived points (e.g. `to_speed`/`to_fluid`), pass `_head=`/`_efficiency=` to preserve measured values rather than re-deriving them.
- **All points in a `PerformanceCurve` must share the same `Fluid` instance** (compared with `Fluid.__eq__`, which compares the full attribute dict including density magnitude/units).
- **Don't mutate `PerformanceCurve` in place.** `to_speed` / `to_fluid` return new instances; preserve that pattern when adding transformations.
- There is a stray `tests/pyproject.toml` that duplicates the root `pyproject.toml` — it is not used by the build and looks accidental; the source of truth is the root file.
- `Point.outlet_pressure` is broken (calls `quantity_factory()` with no args). Treat `Point` as effectively unused — use `DesignPoint` or `TestPoint`.
- README TODO items (open work): viscosity correction, tests, style guidelines, type checking.

## Examples

Working end-to-end Jupyter notebooks live in [examples/](examples/) (`Example_1.ipynb`, `Example_2.ipynb`, and real pump tags like `B-432301D.ipynb`, `52-P-11AB.ipynb`). They are the de-facto integration tests until a real test suite exists — when changing public behavior, run the notebooks and verify the generated `.docx` files in `examples/` still render correctly.
