# Tutorial — Running & Testing CentrifugalPump

A hands-on guide to installing, running, and testing both halves of the project:
the **`pump`** engineering library and the **`pumpflow`** visual workbench.

> **New here?** Read the [Architecture Blueprint](ARCHITECTURE.md) first for the
> big picture, then come back to get it running.

| | |
|---|---|
| **Time to first result** | ~5 minutes (library) · ~8 minutes (GUI) |
| **Verified on** | Python 3.12.13, Linux (WSL2) |
| **You'll end up with** | A passing test suite, a generated chart, and (optionally) the desktop app |

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Running the `pump` library](#3-running-the-pump-library)
4. [Running the `pumpflow` desktop app](#4-running-the-pumpflow-desktop-app)
5. [Testing](#5-testing)
6. [Troubleshooting](#6-troubleshooting)
7. [Quick reference](#7-quick-reference)

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.12+** | Required despite `pyproject.toml` saying `>=3.6` — the code uses 3.12-only syntax (see [Architecture §4](ARCHITECTURE.md#4-coupling-dependencies--risk-spots)). |
| **pip** or **conda/mamba** | Either works; conda env file provided. |
| **A display** | Only for the desktop GUI (§4). The library and tests run headless. |

Check your Python:

```bash
python --version      # must report 3.12 or newer
```

---

## 2. Installation

Clone and enter the repository:

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
```

### Option A — pip (editable, recommended for development)

```bash
pip install -e .[dev]     # library + black/build/pytest
```

This installs the `pump` library and its runtime dependencies
(`matplotlib`, `numpy`, `pint`, `python-docx`, `tabulate`) plus the dev tools.

### Option B — conda / mamba

```bash
mamba env create -f environment.yml
mamba activate pump
pip install -e .[dev]
```

### Add the GUI dependencies (only if you want the desktop app)

PySide6 is **not** declared in `pyproject.toml`, so install it explicitly:

```bash
pip install PySide6 matplotlib numpy
```

Verify the install:

```bash
python -c "import pump; print('pump', pump.__version__, 'OK')"
```

---

## 3. Running the `pump` library

The library is a normal importable package — no app to "launch." Here is the
complete core workflow, end to end. **This snippet is verified to run as written.**

Save as `demo.py` and run `python demo.py`:

```python
import matplotlib
matplotlib.use("Agg")          # headless; drop this line to view interactively

from pump import (
    Q_, Fluid, DesignPoint, TestPoint, PerformanceCurve, PerformanceChecker,
)

# 1) Define the test fluid.
water = Fluid("Water", density=Q_(997, "kg/m**3"))

# 2) Build measured test points (capacity, head, breaking power) at 1750 rpm.
rows = [(0, 117, 180), (300, 110, 210), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
points = [
    TestPoint(fluid=water, capacity=Q_(q, "m**3/h"), speed_of_rotation=Q_(1750, "rpm"),
              _head=Q_(h, "m"), breaking_power=Q_(p, "kW"))
    for q, h, p in rows
]

# 3) Wrap them in a curve (degree-3 polynomial fit, per API 610).
curve = PerformanceCurve(water, points, polynomial_degree=3)
print("Predicted head @ 833 m³/h:", curve.predict_head(Q_(833, "m**3/h")))

# 4) Define the rated/design point and run the API 610 compliance check.
design = DesignPoint(fluid=water, capacity=Q_(833, "m**3/h"),
                     differential_head=Q_(73, "m"),
                     breaking_power=Q_(252, "kW"), head_shutoff=Q_(117, "m"))
checker = PerformanceChecker(design, curve)
print(checker.check_summary)        # per-point pass/fail table

# 5) Save a performance chart.
stream = curve.plot_performance_curve(capacity=Q_(833, "m**3/h"), return_io=True)
with open("performance_curve.png", "wb") as fh:
    fh.write(stream.getvalue())
print("Wrote performance_curve.png")
```

Expected highlights:

```
Predicted head @ 833 m³/h: 73.82384282945986 meter
... a grid table of per-point Head/Shutoff/Power checks ...
Wrote performance_curve.png
```

### Generate a `.docx` report

`ReportGenerator` needs a template (`pump/templates/template_en.docx` ships in the
repo). See [pumpflow data formats](../pumpflow/docs/data_formats.md) for the
`report_data` dict shape, or drive it through the GUI's Report Export node (§4).

### Explore the worked examples

The richest, real-world usage lives in the notebooks:

```bash
jupyter lab examples/        # B-432301D.ipynb, 52-P-11AB.ipynb, Example_1.ipynb, …
```

> The notebook `examples/pump_api610_performance 1.ipynb` is the **reference UX**
> the project is converging toward.

---

## 4. Running the `pumpflow` desktop app

> **Heads-up:** the GUI requires **PySide6** (see §2). If it isn't installed,
> `python -m pumpflow` fails with `ModuleNotFoundError: No module named 'PySide6'`.

Launch from the repository root:

```bash
python -m pumpflow
```

The window opens with a **default pre-wired pipeline** already populated with
seeded single-pump data, so you immediately see corrected points, a fitted curve,
and an APPROVED/REJECTED verdict.

### Canvas controls

| Action | How |
|---|---|
| Open a node's property dialog | **Double-click** the node |
| Wire a link | **Drag** from an output port to a compatible input port |
| Re-wire a single input | **Drag** off the input port |
| Delete node / link | Select, then **Delete** / **Backspace** |
| Pan | **Middle-drag** or **Alt+drag** |
| Zoom | **Mouse wheel** |
| Recompute everything | **F5** (`Canvas ▸ Recompute graph`) |
| Two-pump A/B demo | `Canvas ▸ Add Pump B branch` |

### A first end-to-end run

1. Double-click **Rated Point Input** → confirm the rated duty (Q/H/N/P).
2. Double-click **Test Points Table** → review the grid; the `Head` and `η`
   columns compute live.
3. Watch **Correction → Curve Fit → Compliance** update downstream; the
   Compliance node shows a bold **APPROVED**/**REJECTED** banner.
4. Double-click **Report Export** → `Export .docx` / `.json` / `.png`.

### Save / load your work

- `File ▸ Save project (.pumpflow)` — the whole canvas (nodes, positions, links, settings).
- `File ▸ Import/Export data file (.json)` — the interchange format (rated point + rows).

Both formats are specified in [pumpflow/docs/data_formats.md](../pumpflow/docs/data_formats.md).

For the full UI walkthrough see the [pumpflow User Guide](../pumpflow/docs/user_guide.md).

---

## 5. Testing

> **Current state:** the repo historically shipped *no* automated tests (the
> `tests/` notebooks are demos, not tests). This tutorial adds a real, passing
> **starter suite** at [`tests/test_pump_smoke.py`](../tests/test_pump_smoke.py)
> — 11 fast, Qt-free tests pinning the core library behaviour.

### Run the suite

From the repository root:

```bash
pytest tests/test_pump_smoke.py -v
```

Expected output (verified):

```
tests/test_pump_smoke.py::test_quantity_factory_canonicalizes_capacity PASSED
tests/test_pump_smoke.py::test_quantity_factory_rejects_non_quantity   PASSED
tests/test_pump_smoke.py::test_curve_length_and_sorting                PASSED
tests/test_pump_smoke.py::test_predict_head_matches_data_near_rated    PASSED
tests/test_pump_smoke.py::test_predict_shutoff_head                    PASSED
tests/test_pump_smoke.py::test_mixed_fluid_curve_is_rejected           PASSED
tests/test_pump_smoke.py::test_to_speed_scales_by_affinity_laws        PASSED
tests/test_pump_smoke.py::test_checker_head_tolerance_band             PASSED
tests/test_pump_smoke.py::test_checker_shutoff_tolerance_tier          PASSED
tests/test_pump_smoke.py::test_report_summary_keys                     PASSED
tests/test_pump_smoke.py::test_plot_returns_png_stream                 PASSED

11 passed
```

Run everything pytest can discover:

```bash
pytest -v
```

### What the starter suite covers

| Area | Tests |
|---|---|
| Units foundation | canonicalization to standard units; rejection of non-`Quantity` input |
| Curve container | length, capacity-sorting, mixed-fluid rejection |
| Fitting | predicted head near rated & at shut-off |
| Affinity laws | `to_speed` scales Q∝N and H∝N² |
| API 610 verdict | ±3 % head band, tiered shut-off tolerance, `report_summary` keys |
| Plotting | `plot_performance_curve(return_io=True)` emits a valid PNG (headless) |

### Tips

```bash
pytest -k affinity            # run tests matching a name
pytest -x                     # stop at first failure
pytest --cov=pump             # coverage (needs pytest-cov; in conda env)
```

### Extending it (recommended next steps)

The suite ends with a TODO list. High-value additions, in order:

1. `to_fluid()` density-correction round-trip.
2. `PerformanceFitter` lazy-coefficient memoization.
3. Efficiency from hydraulic ÷ breaking power.
4. **Regression tests** that pin numbers from `examples/*.ipynb` so the notebooks
   become an executable spec.
5. A separate `pytest-qt` suite for `pumpflow` node `compute()` logic (keep it
   isolated — it needs a `QApplication` and PySide6).

> **Known issues that tests should eventually catch** (see
> [Architecture §4](ARCHITECTURE.md#4-coupling-dependencies--risk-spots)): the
> `pint` `NameError` in `unit_conversion.py`, the broken `Point.outlet_pressure`,
> and the `requires-python` metadata mismatch.

---

## 6. Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `ModuleNotFoundError: No module named 'PySide6'` | GUI deps not installed — `pip install PySide6 matplotlib numpy` (§2). |
| `SyntaxError` on import | You're on Python < 3.12. Upgrade; the code uses 3.12 syntax. |
| `FileNotFoundError: template_en.docx` | Pass a template path to `ReportGenerator`, or set the *Template* field in the Report Export dialog. |
| A Matplotlib window blocks a script/test | Add `import matplotlib; matplotlib.use("Agg")` **before** importing `pump`. |
| App opens but a node shows amber/red | That's the status system working — open the node (double-click) to read the message; amber = invalid input, red = error. |
| `pytest` finds no tests | Run from the **repo root** and point at the file: `pytest tests/test_pump_smoke.py`. |

---

## 7. Quick reference

```bash
# --- install -------------------------------------------------------------
pip install -e .[dev]                 # library + dev tools
pip install PySide6 matplotlib numpy  # GUI deps (optional)

# --- run -----------------------------------------------------------------
python demo.py                        # the library snippet from §3
python -m pumpflow                    # the desktop workbench
jupyter lab examples/                 # the worked notebooks

# --- test ----------------------------------------------------------------
pytest tests/test_pump_smoke.py -v    # the starter suite (11 tests)
pytest -v                             # everything discoverable
```

---

*See also: [Architecture Blueprint](ARCHITECTURE.md) · [pumpflow docs](../pumpflow/docs/index.md) · [`UI_SPEC.md`](../UI_SPEC.md)*
