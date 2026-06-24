# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

`centrifugal-pump` helps engineers assess an **API 610** pump during its Performance and Mechanical Running Test (Factory Acceptance Test). It computes hydraulic quantities, fits polynomials to measured test points, checks results against API 610 tolerances, and generates Word (`.docx`) acceptance reports.

The repo is **two stacked subsystems**:

- **[`pump/`](pump/)** — the headless physics **library** (Pint units, fluids, points, performance curves, compliance checking, `.docx` reporting). Source of truth for all physics.
- **[`pumpflow/`](pumpflow/)** — a **PySide6 visual workbench** (an Orange3-style node canvas) that orchestrates the library into a drag-and-wire workflow. It re-implements **no** physics; `pumpflow/binding.py` is the *only* place that calls into `pump`.

The driving reference UX is the notebook [`examples/pump_api610_performance 1.ipynb`](examples/pump_api610_performance%201.ipynb) — the library and workbench are being evolved to host that workflow. [`UI_SPEC.md`](UI_SPEC.md) is the authoritative spec for `pumpflow` (its sections are cited throughout the code as `UI_SPEC §N`).

## Common commands

```bash
pip install -e ".[dev]"              # library + black / build / pytest
pip install -e ".[docs]"             # + sphinx / furo / myst-parser for the docs site

# Tests (pytest config in pyproject.toml: testpaths = tests + pump, --doctest-modules)
pytest                               # full suite: tests/ + pump/ docstring examples
pytest tests/test_utilities.py       # one file
pytest tests/test_affinity.py::test_name   # one test
pytest -k affinity                   # by keyword
pytest --doctest-modules pump        # docstring examples only

black .                              # format (only configured quality tool)

python -m build                      # sdist + wheel -> dist/
sphinx-build -b html docs docs/_build/html   # docs site

# Visual workbench
pip install PySide6 matplotlib numpy
python -m pumpflow                   # opens with a pre-wired default pipeline
```

There is **no lint or type-check** configured (only `black`). `pytest` collects `tests/` plus `pump/` docstrings as doctests, but deliberately **does not** crawl `pumpflow/` (it would need PySide6) — `pumpflow/nodes/test_points.py` is a Qt widget, *not* a pytest file despite the `test_` prefix.

## Architecture — the `pump` library

### The units spine: everything flows through `quantity_factory`

Built around Pint quantities normalized to a fixed table of standard units. [pump/utilities/unit_conversion.py](pump/utilities/unit_conversion.py) defines:

- `STANDARD_UNITS` — dimensionality → standard-unit map (capacity → `m**3/h`, pressure → `kgf/cm**2`, power → `kW`, …) with per-context overrides (`pressure` has `default`/`atm`/`delta`).
- `quantity_factory(q, context="default")` — the single entry point for normalization; dispatches by `q.dimensionality`.
- `extract_context(key)` — when attributes are set via `**kwargs`, the name is split on `_`; if the first token is a known context (`atm`, `delta`, `default`), that context drives conversion. **Attribute naming controls unit handling.** Prefer descriptive prefixes that are *not* context names (`inlet_…`, `outlet_…`) unless context-routing is intended.

To add a new dimensionality (e.g. viscosity correction — a roadmap item), extend `STANDARD_UNITS` rather than calling `.to()` ad-hoc.

### Domain model: `Fluid` + the `BasePoint` hierarchy

- [pump/utilities/fluid.py](pump/utilities/fluid.py) — `Fluid(name, density, **kwargs)`; extra kwargs become Pint attributes.
- [pump/point.py](pump/point.py):
  - `BasePoint(fluid, capacity, **kwargs)` — generic point; dynamic kwargs become Pint attributes.
  - `DesignPoint` — adds `differential_head` + derived hydraulic properties (`specific_energy`, `power_output`, `outlet_pressure`, velocity/elevation heads); degrades gracefully when optional inputs are absent.
  - `TestPoint` — measured point; `compute_head`/`head`, `compute_hydraulic_power`, `compute_efficiency` (needs `breaking_power`). Sortable by capacity.
  - `Point.outlet_pressure` is **broken** (calls `quantity_factory()` with no args). Treat `Point` as dead code — use `DesignPoint`/`TestPoint`.
- **Property caches use leading underscores** (`_head`, `_efficiency`). When constructing derived points (e.g. in `to_speed`), pass `_head=`/`_efficiency=` to preserve measured values rather than re-deriving from pressures/diameters that may be absent.

### `PerformanceCurve` + checking

[pump/performance_curve.py](pump/performance_curve.py):

- `PerformanceFitter(points, polynomial_degree=4)` — lazy, cached numpy polynomial fits for head/efficiency/power vs capacity.
- `PerformanceCurve(fluid, points, polynomial_degree=4)` — owns a fitter and sorted `TestPoint`s that **must all share the same `Fluid`** (enforced in `__init__` via `Fluid.__eq__`). Provides `predict_head`/`predict_efficiency`/`predict_breaking_power`, `plot_performance_curve(...)` (returns a `BytesIO` PNG for reports), and two transforms that **always return new instances** (never mutate in place):
  - `to_speed(new_speed)` — affinity laws: Q ∝ N, H ∝ N², P ∝ N³.
  - `to_fluid(new_fluid)` — same head, `breaking_power` recomputed for the new density (efficiency assumed invariant).
- `PerformanceChecker(design_point, performance_curve)` — API 610 tolerances: head ±3%; shutoff head ±10/8/5% by differential head band (≤75 / ≤300 / >300 m); breaking power +4%. Produces `check_summary` / `report_summary` consumed by the reporter.

### Report generation

[pump/utilities/report.py](pump/utilities/report.py) renders `.docx` from `pump/templates/template_{en,pt}.docx` via `python-docx`. Localization is gettext catalogs under [pump/utilities/locales/](pump/utilities/locales/) (`pt` has a compiled `.mo`; `en` falls back to source strings). When changing template structure, update **both** templates, add strings to **both** `.po` files, and recompile pt: `msgfmt messages.po -o messages.mo`.

## Architecture — the `pumpflow` workbench

A thin, reactive layer on top of `pump`, built natively on PySide6 `QGraphicsView` (no NodeGraphQt / Orange3 runtime). Layers (see `pumpflow/__init__.py`):

- **`signals.py`** — typed, **immutable** `@dataclass` payloads that flow along links (`RatedPoint`, `TestPointSet`, `CorrectedCurve`, `FittedModel`, `ComplianceResult`, `ReportBundle`). A node re-emits a *fresh* instance on any change, mirroring the library's "return a new instance" convention.
- **`binding.py`** — the **only** adapter into `pump`. Flat signal payloads → library constructors and back.
- **`mathx.py`** — `NaturalCubicSpline` + `water_density_kgm3`, ported from the reference notebook because they aren't in `pump` yet (UI_SPEC §4 note). Degree-3 polynomial is the API 610 primary fit; the spline is an optional secondary overlay.
- **`nodes/`** — the seven workflow widgets (`BaseNode` subclasses) + property dialogs. `BaseNode.compute(inputs) -> {output_port: payload}` is the Qt-agnostic core; `registry.py` maps `kind` → class.
- **`canvas/`** — `GraphScene` holds `NodeItem`/`EdgeItem`, handles interactive wiring (output ports **fan out**; Report Export input is **multi-connection/merge**), and `evaluate()` recomputes the graph in **topological order** so upstream edits live-update downstream. `to_dict`/`load_dict` (de)serialize the canvas.
- **`persistence.py`** — `.pumpflow` project files and data-exchange JSON (UI_SPEC §6). On disk it stores **only plain magnitudes + units** so the format stays stable; live `pint`/`pump` objects exist only at runtime.
- **`app.py`** — `MainWindow`, the default pre-wired pipeline, entry point (`python -m pumpflow`). Owns project management: `_dirty`/`_current_path` state, a Save/Discard/Cancel `_maybe_save()` guard (run before New/Open/close — `closeEvent` hooks it so unsaved work is never lost), and a ` *` window-title dirty marker. `File > New` (`Ctrl+N`) loads an **empty** canvas; the pre-wired pipeline is only the startup default.
- **`numfmt.py` / `style.py` / `sample_data.py`** — support modules: locale-tolerant number parse/format (UI_SPEC §5.2/§6.2), the global Qt stylesheet, and a seeded realistic single-pump FAT dataset, respectively.

### Key engineering constraint (shared-fluid)

`PerformanceCurve` requires one `Fluid` for all points. In the workbench, per-row `Head`/`η` are computed with each row's own water density and **pinned** onto the `TestPoint`s (`_head`/`_efficiency`), so the curve's single test-water fluid is effectively just a label; correction then follows `to_speed` → `to_fluid` exactly.

### Identity convention

`RatedPoint.tag` is the **service/datasheet** tag, *shared* across all pump branches. `TestPointSet.pump_tag` is the **physical unit** tag, *unique per branch*. Every downstream signal carries `pump_tag` so Report Export (and plots/verdicts) can key datasets unambiguously — including the A/B two-pump case.

## Conventions and gotchas

- **Always pass `Q_` (Pint quantities), never raw numbers** into library constructors — non-`Quantity` input raises `ValueError`.
- **Attribute naming controls unit conversion** (see `extract_context` above).
- **Don't mutate `PerformanceCurve` in place**; `to_speed`/`to_fluid` (and `pumpflow` signals) return new instances — preserve that pattern.
- **All points in a `PerformanceCurve` must share the same `Fluid`.**
- **`pumpflow` must not re-implement physics** — route everything through `pump` via `binding.py`.
- Roadmap / open work: viscosity correction, report export to PDF/HTML/JSON, library gaps (system curve, NPSH margin, impeller trim, multi-pump compare), `black` + type-checking in CI.

## Workflow

Development is organized as **8-hour sprints** under [docs/sprints/](docs/sprints/) (each is one focused `.md` landing as a single commit on its branch), driven by demos in `tests/utilities_test.ipynb` that become assertions. The product audience and use-case registry live under [docs/product/](docs/product/); architecture decisions under [docs/adr/](docs/adr/). Priorities follow the FAT engineer use cases (UC-02 performance verification, UC-06 affinity speed change, UC-09 `.docx` report).
