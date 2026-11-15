# Centrifugal Pump

A set of tools to help engineers assess the condition of an **API 610** pump during
its Performance and Mechanical Running Test (Factory Acceptance Test) trials.

The repository is two stacked subsystems:

- **[`pump/`](pump/)** — a layered Python **library** of pump physics: Pint-based
  units, fluids, points, performance curves, API 610 compliance checking, and
  `.docx` reporting.
- **[`pumpflow/`](pumpflow/)** — a PySide6 **visual workbench** that orchestrates the
  library into a drag-and-wire node workflow (intended to replace the notebook
  workflow with a guided UI).

> 📚 **Documentation:** the architecture blueprint, run/test tutorial, audience &
> use-case registry, and the auto-generated API reference live under
> [`docs/`](docs/) and build into a [Sphinx](https://www.sphinx-doc.org) site (see
> [Documentation](#documentation)). Development is organized as
> [8-hour sprints](docs/sprints/README.md).

## Quickstart

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
pip install -e ".[dev]"     # library + black / build / pytest
pytest                       # tests/ + pump/ doctests, all green
```

A 30-second FAT computation:

```python
from pump import Q_, Fluid, DesignPoint, TestPoint, PerformanceCurve, PerformanceChecker

water = Fluid("Water", density=Q_(997, "kg/m**3"))
points = [
    TestPoint(fluid=water, capacity=Q_(q, "m**3/h"),
              speed_of_rotation=Q_(1750, "rpm"), _head=Q_(h, "m"),
              breaking_power=Q_(p, "kW"))
    for q, h, p in [(0, 117, 180), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
]
curve = PerformanceCurve(water, points, polynomial_degree=3)
rated = DesignPoint(fluid=water, capacity=Q_(833, "m**3/h"),
                    differential_head=Q_(73, "m"), breaking_power=Q_(252, "kW"),
                    head_shutoff=Q_(117, "m"))
print(PerformanceChecker(rated, curve).report_summary)
```

## The visual workbench

```bash
pip install PySide6 matplotlib numpy
python -m pumpflow
```

Then **File ▸ Open** the bundled
[`examples/sample_project.pumpflow`](examples/sample_project.pumpflow) to load a
complete single-pump FAT pipeline (Rated Point + Test Points → Speed Correction →
Curve Fit → Plot / Compliance → Report Export).

## Testing

```bash
pytest                          # full suite (tests/ + pump/ doctests)
pytest tests/test_utilities.py  # one file
pytest -k affinity              # by keyword
pytest --doctest-modules pump   # docstring examples only
```

The suite pins the units/`Fluid` spec, the API 610 compliance bands and affinity
speed-correction (UC-02 / UC-06), and a `.pumpflow` persistence round-trip. The Qt
round-trip skips cleanly when PySide6 is not installed. See the
[Run & Test tutorial](docs/RUN_AND_TEST.md).

## Documentation

```bash
pip install -e ".[docs]"
sphinx-build -b html docs docs/_build/html
# open docs/_build/html/index.html
```

The site combines the hand-written guides (architecture, tutorials, ADRs, product
docs) with an API reference auto-generated from the NumPy-style docstrings. It is
configured for [Read the Docs](https://readthedocs.org) via
[`.readthedocs.yaml`](.readthedocs.yaml).

## Installation & packaging

### Regular users

```bash
pip install .
```

### Developers (conda/mamba)

A conda environment file is provided (Python 3.12, Jupyter, plotting libraries):

```bash
mamba env create -f environment.yml
mamba activate pump
mamba env update -f environment.yml   # after editing environment.yml
```

### Building distributions

```bash
pip install build
python -m build      # -> dist/*.tar.gz and dist/*.whl
```

## Capabilities

Every use case has a worked, executable notebook (public `pump` API, Pint units,
final assertions — all run in CI) and a workbench node:

| UC | What it does | Notebook | Workbench node(s) |
|----|--------------|----------|-------------------|
| UC-00 | Engineer's own units (Pint end to end, gauge/absolute, value+unit files) | [UC-00](use_cases/UC-00_utilities_demo.ipynb) | every input field |
| UC-01 | Select a pump from a curve catalogue (speed / trim adaptation, POR) | [UC-01](use_cases/UC-01_selection.ipynb) | Selection |
| UC-02 | Verify FAT performance vs API 610 (edition-aware tolerances) | [UC-02](use_cases/UC-02_performance_verification.ipynb) | Test Points → Correction → Curve Fit → Compliance |
| UC-03/04 | System curve and operating point | [UC-03/04](use_cases/UC-03-04_system_operating_point.ipynb) | System Curve, Operating Point |
| UC-05 | NPSH available / required and margin | [UC-05](use_cases/UC-05_npsh.ipynb) | NPSH |
| UC-06 | Speed change (affinity) | [UC-06](use_cases/UC-06_affinity_speed_change.ipynb) | Correction |
| UC-07 | Impeller trim | [UC-07](use_cases/UC-07_trim.ipynb) | Trim |
| UC-08 | Compare pumps (twin A vs B) | [UC-08](use_cases/UC-08_compare.ipynb) | Explorer Δ, report "Comparison" |
| UC-09 | Reports: Word, LaTeX, PDF, HTML (en/pt) | [UC-09](use_cases/UC-09_reports.ipynb) | Report Export, `python -m pumpflow.export_cli` |
| UC-10 | Learn the fundamentals | [concepts](docs/concepts/) | formula tooltips |
| UC-11 | Mechanical running test acceptance | [UC-11](use_cases/UC-11_mechanical_run.ipynb) | Mechanical Run |
| — | Viscosity correction (HI 9.6.7) | [viscosity](use_cases/viscosity_HI967.ipynb) | Correction ("apply viscosity") |

Acceptance values (API 610 tolerances, vibration, POR) are data in
`pump/standards/api610.toml` with a `source` and a `verified` flag; verdicts on
unverified criteria are labelled as provisional.

**Status:** delivered by project
[001_masterpiece](docs/changes/001_masterpiece/README.md) (14 sprints).

