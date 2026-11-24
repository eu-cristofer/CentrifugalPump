# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

`centrifugal-pump` helps engineers witness an **API 610** pump's Performance and Mechanical Running Test (Factory Acceptance Test). It computes hydraulic quantities with Pint units end to end, fits curves to measured test points, corrects them (speed, density, HI 9.6.7 viscosity, impeller trim), judges them against **edition-aware** acceptance criteria (API 610 8th/10th/11th/12th plus client overlays such as Petrobras N-553), and writes Word, LaTeX, PDF and HTML reports in English and Portuguese.

The repo is **two stacked subsystems**:

- **[`pump/`](pump/)**: the headless physics **library** (units, fluids, points, curves, acceptance, NPSH, mechanical run, system curve, selection, reporting). It is the source of truth for all physics and every verdict.
- **[`pumpflow/`](pumpflow/)**: a **PySide6 visual workbench** (node canvas). It re-implements **no** physics; the `pumpflow/binding/` package is the *only* place that calls into `pump`.

[`docs/UI_SPEC.md`](docs/UI_SPEC.md) is the authoritative spec for `pumpflow`; the code cites it as `UI_SPEC §N`.

## Common commands

```bash
pip install -e ".[dev,gui]"          # library + workbench + pytest / black / mypy
pip install -e ".[docs]"             # + sphinx / furo / myst-parser
mamba env create -f environment.yml  # optional conda env "pump" (channels live in .condarc, not the yml)

pytest                               # tests/ + pump/ doctests (+ notebooks in tests/test_notebooks.py)
pytest tests/test_acceptance.py      # one file
pytest -k verdict                    # by keyword
pytest tests/test_affinity.py::test_to_speed_round_trip_is_identity   # one test

black <file>                         # only on black-clean files (CI checks a listed set)
mypy pump --ignore-missing-imports   # CI job, non-blocking until its backlog is fixed
sphinx-build -b html docs docs/_build/html

python -m pumpflow                   # the workbench
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/r   # headless report export
python use_cases/build_notebooks.py  # regenerate the generated notebooks (edit the script, not the .ipynb)

npm --prefix web ci                  # the web version (Node 22): install
npm --prefix web run vendor          # fill web/public/py (Pyodide, wheels, project wheel; the only networked step)
npm --prefix web run dev             # dev server
npm --prefix web run check           # typecheck + lint + vitest
npm --prefix web run parity          # Pyodide = desktop on the fixture projects
npm --prefix web run build           # web/dist, the offline app (see docs/web.md)
```

`pytest` collects `tests/` plus `pump/` docstrings; it does **not** crawl `pumpflow/` (a Qt package). `pumpflow/nodes/test_points.py` is a Qt widget, not a test. GUI tests run Qt offscreen (`QT_QPA_PLATFORM=offscreen`). Do not open Qt windows and call `processEvents()` in tests after a modeless child window was left open: it can segfault.

CI (`.github/workflows/ci.yml`): tests on Python 3.12 and 3.13 (blocking), black on a listed file set, a LaTeX job that exports the P-9001A PDF, and mypy and Sphinx `-W` (non-blocking backlogs listed in `docs/changes/NEXT_STEPS.md`).

## Architecture: the `pump` library

### Units
- Everything is a Pint quantity: `Q_` from `pump`.  `quantity_factory(q, context=)` in [pump/utilities/unit_conversion.py](pump/utilities/unit_conversion.py) normalises to `STANDARD_UNITS`.  When kwargs set attributes, the first `_` token of the name can select a context (`atm`, `delta`, `default`), so **attribute naming controls unit handling**.
- `pump.Pressure` ([pump/utilities/pressure.py](pump/utilities/pressure.py)) carries the gauge/absolute reference; Pint has none.  `pump.constants.G = 9.80665 m/s²`: never hard-code 9.81.
- `pump.quantity_io.to_json/from_json` is the single `{"value", "unit"}` serialisation.

### Domain model
- `Fluid(name, density, **kwargs)` and `Water` (density, viscosity, vapour pressure vs temperature) in [pump/utilities/fluid.py](pump/utilities/fluid.py).
- [pump/point.py](pump/point.py): `BasePoint` → `DesignPoint` (rated point: `differential_head`, `head_shutoff`, `breaking_power`, …) and `TestPoint` (measured; `compute_head` = pressure + velocity + elevation head when the geometry is given).  **Property caches use leading underscores**: pass `_head=` / `_efficiency=` to pin measured values on derived points.

### Curves and transforms ([pump/performance_curve.py](pump/performance_curve.py))
- `PerformanceCurve(fluid, points, polynomial_degree)`: every point **must share one `Fluid`**.  `predict_head/efficiency/breaking_power`, `plot_performance_curve`.
- Transforms **always return new instances**: `to_speed` (affinity), `to_fluid` (density), `to_viscous` (HI 9.6.7, [pump/viscosity.py](pump/viscosity.py)), `to_diameter` (trim, [pump/trim.py](pump/trim.py)).
- `pump.fitting`: `NaturalCubicSpline`, `r_squared` (`pumpflow/mathx.py` is only a re-export shim).

### Acceptance: one engine ([pump/acceptance.py](pump/acceptance.py), ADR 0012)
- Criteria are **data**: [pump/standards/api610.toml](pump/standards/api610.toml) (one table per edition) and [pump/standards/clients/*.toml](pump/standards/clients/) (overlays).  `AcceptanceCriteria.load("api610:8", client="n553")`.
- Every table has a clause-level `source` and `verified`; `unverified` lists open parts, `performance_unverified` those that affect the performance verdict.  A merged sub-table is verified only if every layer is.  **Never invent a standard value**: unknown values ship `verified = false` with an honest `source`, and verdicts on them are labelled provisional.
- `evaluate_performance(...)` is the **only** performance-verdict implementation.  Rows are `pass` / `fail` / `info` / `not evaluated`.  `approved = passed and complete`; a check that cannot be computed is never a silent pass ("NOT FULLY ASSESSED").  `PerformanceChecker` and `binding.check_compliance` are views of it.
- API 610 facts encoded (checked against the 8th, 11th and 12th texts): efficiency is **not** a rated value (info only unless the purchaser sets a tolerance); shut-off bands split at 150/300 m in the 8th and 75/300 m in the 11th/12th; rising-curve rule; rated NPSH +0 % against the quoted NPSHr; test speed within 3 %.
- Other verdicts: `pump.npsh` (margin rule from the client overlay plus quoted NPSHr), `pump.mechanical_run` (vibration in RMS, stabilisation, duration).

### Other engineering modules
`system_curve.py` + `operating_point.py` (UC-03/04), `catalogue.py` (selection, UC-01), `compare.py` (A vs B, UC-08), `npsh.py` (UC-05), `mechanical_run.py` (UC-11), `vibration.py` (API 610 pump types → vibration measurement locations, the 11th/12th high-speed rule and its chart; limits in `[editions."N".vibration]`, selected by `RatedPoint.pump_type`).

### Reports ([pump/utilities/report.py](pump/utilities/report.py), `report_latex.py`, `report_html.py`)
docx from `pump/templates/template_{en,pt}.docx`, plus LaTeX/PDF and self-contained HTML.  `pump/utilities/test_summary.py` writes the API 610 **test data summary** (Annex M / 8th App. T) as docx, tex, pdf and xlsx (`openpyxl` is the optional `[xlsx]` extra); its vibration columns come from the optional Test Points vibration columns, and its charts (`annex_m_charts.py`) follow the Annex M Figure M.3 test-curve format and the Figure M.4 test-points/vibration format.  Shared helpers (cover, signatures, verdict sentences) live in `report.py`.  Strings come from gettext catalogs in `pump/utilities/locales/{en,pt}/LC_MESSAGES/messages.po`; compiled `.mo` files are git-ignored and a `.po` fallback parser is used.  Add every new string to **both** `.po` files.

## Architecture: the `pumpflow` workbench

A thin reactive layer on PySide6 `QGraphicsView`:

- **`signals.py`**: immutable dataclass payloads carrying Pint quantities (`RatedPoint`, `TestPointSet`, `CorrectedCurve`, `FittedModel`, `ComplianceResult`, `NPSHSet`, …).  Nodes emit fresh instances.
- **`binding/`**: the **only** adapter into `pump` (signals ↔ library objects, display floats), split by topic: `_common`, `curves`, `acceptance`, `reports`, `engineering`, `summary` (Annex M test data summary); `from pumpflow.binding import X` re-exports everything.  It holds no physics or verdict logic.
- **`nodes/`**: 18 node kinds (`BaseNode` subclasses; `registry.py` maps `kind` → class).  `compute(inputs) -> {port: payload}` is the Qt-agnostic core; `create_dialog` builds the property window from helpers in `nodes/ui.py` (`UnitField`, `PressureField`, `BeforeAfterTable`, `info_button`, …).
- **`canvas/`**: `GraphScene` (wiring, topological `evaluate()`, `to_dict`/`load_dict`); it evaluates through `engine`.
- **`engine.py`**: the Qt-free graph (`Graph`, `topo_order`, `evaluate_in_order`) shared by the canvas, `export_cli`, the tests and the web.  Nodes import Qt only inside `create_dialog` (`tests/test_qt_free_engine.py` guards it).
- **`webapi.py`**: the plain-JSON boundary for the browser (`catalog`, `evaluate`, `default_settings`, `export_report`).  TypeScript never computes; it renders what `webapi` returns.
- **`web/`** (project 002_web, ADR 0013): React Flow + TypeScript front end; the Python runs in Pyodide in a Web Worker.  The offline bundle in `web/public/py` is git-ignored.  Witness kinds have side-panel forms; LaTeX/PDF stays desktop-only.  CI job `web` runs check, parity and build.
- **`persistence.py` + `settings_codec.py`**: `.pumpflow` **schema v2**, where every quantity is `{"value","unit"}` (ADR 0011), with a lossless v1 → v2 migration.  Optional fields use `OptDisp` and are **omitted when unset**, so older files re-save byte-identical.  Do not add always-present default keys to an existing node's settings: it breaks the round-trip tests.
- **`units.py`**: the display-unit menus and presets (SI/US).  **`explain.py`**: formula tooltips.  **`export_cli.py`**: headless export.  **`app.py`**: `MainWindow`.

### Key constraints
- **Shared fluid**: per-row head/η use each row's water density and are pinned on the `TestPoint`s; the curve's fluid is a label, then `to_speed` → `to_fluid`.
- **Identity**: `RatedPoint.tag` is the service tag shared by all branches; `TestPointSet.pump_tag` is the physical unit (unique per branch) and is carried downstream (A/B case).

## Conventions and gotchas

- **Design tokens only**: colours, font sizes, radii and spacing come from `pump/design/tokens.json` through `pump.design` (`color`, `length`, `render` for `@token` stylesheets) or `pumpflow.style.qcolor`. No `#rrggbb` in code (`tests/test_design_tokens.py` fails); see `docs/design-system.md`.
- Pass `Q_` quantities into library constructors; raw numbers raise `ValueError`.
- Don't mutate curves in place; transforms and signals return new instances.
- `pumpflow` must not re-implement physics or verdicts.
- Regression fixture: `examples/user/P-9001A_MRT_reference.pumpflow` must keep exporting with the same verdicts (`python -m pumpflow.export_cli …`); `tests/fixtures/v1/expected.json` pins node statuses.  Change it only for an intended, documented change.
- `examples/sample_project.pumpflow` must equal `pumpflow.sample_data.sample_project_doc()` (`tests/test_persistence_roundtrip.py`); regenerate it from that builder, never hand-edit the JSON.
- `AGENTS.md` predates the `binding/` package split and the `[dev,gui]` install; where it disagrees with this file, this file wins.
- **Confidential material never goes into git**: customer files (PDFs, real `.pumpflow` projects, real reports, the company report form) live only in the private data folder `../CentrifugalPump-data/`, and the licensed standard texts in `marker-output/` (git-ignored).  Examples use anonymised tags (`P-9xxx`, "Vendor A"); never write a real tag, vendor, customer or document number in a tracked file or commit message.  Install the leak guard once per clone (`sh tools/install_hooks.sh`); it scans every push against `../CentrifugalPump-data/wordlist.txt`.  Quote only clause numbers and short phrases from standards.
- After changing Python used by the web, run `npm --prefix web run vendor` (the wheel in `web/public/py` is rebuilt only by vendor) and `npm --prefix web run parity`.
- Training material (`docs/training/`, `docs/concepts/`, the TR/UC notebooks) is updated with every rule change.

## Workflow

- **Repositories**: this public repo holds all code; real customer projects, the anonymisation map (`map.yaml`, used by `tools/anonymise.py`), the leak-guard word list and the real-case verdict check (`check.sh`, via `tools/verdicts.py`) live in the private sibling `../CentrifugalPump-data/`.  The pre-split history is the private, frozen `CentrifugalPump-archive`.
- Larger work is planned as sprint projects with the `sprint-loop` skill under [docs/changes/](docs/changes/) (`001_masterpiece` is complete).  Open items live in [docs/changes/NEXT_STEPS.md](docs/changes/NEXT_STEPS.md).
- Architecture decisions are in [docs/adr/](docs/adr/) (latest: 0013, the web version in Pyodide; 0012, the single verdict engine).  The use-case registry is [docs/product/use-cases.md](docs/product/use-cases.md), with worked notebooks in [use_cases/](use_cases/).
- Commit attribution and "commit/push only when asked" follow the session instructions.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
