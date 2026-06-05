# Overview & quickstart

A self-contained tour. For the full architecture and run/test tutorials, see
[`docs/ARCHITECTURE.md`](https://github.com/eu-cristofer/CentrifugalPump/blob/main/docs/ARCHITECTURE.md)
and
[`docs/RUN_AND_TEST.md`](https://github.com/eu-cristofer/CentrifugalPump/blob/main/docs/RUN_AND_TEST.md)
in the repository.

## Install

```bash
pip install -e .            # library + runtime deps
pip install -e ".[dev]"     # + black / build / pytest
pip install -e ".[docs]"    # + sphinx / furo / myst-parser
```

The PySide6 workbench additionally needs `pip install PySide6`.

## A 30-second FAT computation

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

checker = PerformanceChecker(rated, curve)
print(checker.report_summary)
```

## Run the tests

```bash
pytest                      # tests/ + pump/ doctests
pytest --doctest-modules pump
```

## The visual workbench

```bash
pip install PySide6 matplotlib numpy
python -m pumpflow
```

Then **File ▸ Open** the bundled
[`examples/sample_project.pumpflow`](https://github.com/eu-cristofer/CentrifugalPump/blob/main/examples/sample_project.pumpflow)
to load a complete single-pump FAT pipeline.

## How the pieces fit

```{mermaid}
flowchart LR
    subgraph App["pumpflow/ — visual workbench (PySide6)"]
        NODES["widget nodes"] --> BIND["binding.py (only bridge)"]
    end
    subgraph Lib["pump/ — engineering library"]
        BIND --> CURVE["PerformanceCurve + Checker"]
        CURVE --> UNITS["Pint units · Fluid"]
        CURVE --> REPORT["ReportGenerator (.docx)"]
    end
```

(The Mermaid diagram renders on Read the Docs when the `sphinxcontrib-mermaid`
extension is enabled; locally it shows as a fenced code block.)
