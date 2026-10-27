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

## Roadmap

Current value targets the **FAT engineer** (see
[audience](docs/product/audience.md) and
[use-case registry](docs/product/use-cases.md)). Shipped MVP: performance
verification (UC-02), VFD/affinity speed change (UC-06), `.docx` report generation
(UC-09).

Planned (v1.1+):

1. Viscosity correction
2. Report export to PDF / HTML / JSON (UC-09 follow-on; `.docx` works today)
3. Library gaps: pump selection, system curve, operating point, NPSH margin,
   impeller trim, multi-pump comparison (UC-01/03/04/05/07/08)
4. Style guidelines (`black`) and type checking in CI

> ~~Add testing~~ — done: see [Testing](#testing) and
> [ADR 0001](docs/adr/0001-establish-automated-test-harness.md).
