# Build & Development Guide

This guide covers how to set up a development environment for the `centrifugal-pump` project, including both the `pump` library and the `pumpflow` visual workbench.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.12+** | The codebase uses Python 3.12 syntax. |
| **pip** or **conda/mamba** | For managing environments and dependencies. |
| **Git** | For cloning the repository. |
| **Display Server** | Required for running the `pumpflow` GUI. The library and tests can be run headless. |

---

## 2. Environment Setup

First, clone the repository and navigate into the project directory:

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
```

Next, install the project in editable mode with development dependencies. This will install the `pump` library, its core dependencies (`numpy`, `pint`, `matplotlib`, etc.), and testing tools like `pytest`.

```bash
# Install the library and developer tools
pip install -e ".[dev]"
```

### GUI Dependencies

The `pumpflow` visual workbench is built on PySide6 and pyqtgraph. These are heavy dependencies and are kept optional. To install them, run:

```bash
# Install GUI-specific dependencies
pip install -e ".[gui]"
```

Alternatively, you can install them manually:

```bash
pip install PySide6 pyqtgraph
```

---

## 3. Running the Applications

### `pump` Library (Headless)

The `pump` library is a standard Python package. You can import and use its components in any Python script or notebook. The reference workflow can be found in `examples/pump_api610_performance 1.ipynb`.

### `pumpflow` Visual Workbench

With the GUI dependencies installed, you can launch the application from the project root:

```bash
python -m pumpflow
```

The application will start, showing the Welcome Dialog which provides access to recent projects and bundled examples.

---

## 4. Code Quality & Testing

### Formatting

The project uses `black` for code formatting. To format the entire codebase, run:

```bash
black .
```

### Running Tests

The test suite is built on `pytest`. The primary tests for the `pump` library are located in the `tests/` directory.

To run the full test suite:

```bash
pytest
```

This command will discover and run tests in `tests/` and also execute doctests within the `pump/` library modules, as configured in `pyproject.toml`.

**Note:** The `pumpflow/` GUI code is not part of the standard `pytest` run, as it requires a Qt application instance.

---

## 5. Building Documentation

The project documentation is built using Sphinx. To build the HTML documentation:

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Build the HTML site
sphinx-build -b html docs docs/_build/html
```

The output will be located in the `docs/_build/html` directory.

---

## 6. Creating a Distributable Package

To build the source distribution (`sdist`) and wheel for the `pump` library, use the standard `build` package:

```bash
python -m build
```

The generated packages will be placed in the `dist/` directory.