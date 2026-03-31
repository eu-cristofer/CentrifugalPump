# Centrifugal Pump

A set of tools to help engineers assess the condition of an API 610 pump during its Performance and Mechanical Running Test trials.

# Installation and Packaging Guide

This guide explains how to install, develop, and package the `centrifugal-pump` Python library.

## Installing the Package

### For regular users

To install the package with its core dependencies:

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
pip install .
```

### For developers (pip)

If you plan to modify or contribute to the project, install it in editable mode with development dependencies:

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
pip install -e .[dev]
```

This installs the package in editable mode (`-e`) along with all development tools.

### For developers (conda/mamba)

A conda environment file is provided for a reproducible development setup (Python 3.12, Jupyter, plotting libraries, etc.):

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
cd CentrifugalPump
mamba env create -f environment.yml
mamba activate pump
```

To update the environment after changes to `environment.yml`:

```bash
mamba env update -f environment.yml
```

## Building the package

Ensure you have the necessary build tools installed:

```bash
pip install build
```

Then, generate the distribution files:

```bash
python -m build
```

This creates the `dist/` folder containing:

- A source distribution (`.tar.gz`)
- A wheel distribution (`.whl`)

# TODO

1. Add viscosity correction
2. Add testing
3. Check style guidelines
4. Run type checking
