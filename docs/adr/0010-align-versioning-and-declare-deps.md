# ADR 0010 — Align versioning & declare GUI dependencies

- **Status:** Proposed
- **Criticality:** 🟢 Low
- **Date:** 2026-06-05
- **Related:** [Architecture §4.10](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)

## Context

Several packaging/metadata inconsistencies create friction:

- **Version drift:** `pump/__init__.py` declares `__version__ = "0.0.1"`, while
  `pyproject.toml` says `0.1.0` and `pumpflow/__init__.py` says `0.1.0`.
- **Undeclared GUI deps:** `pumpflow` requires **PySide6** (and matplotlib/numpy),
  but PySide6 is not declared anywhere in packaging. Users hit
  `ModuleNotFoundError` only at runtime (see [Run & Test §6](../RUN_AND_TEST.md#6-troubleshooting)).
- **Duplicate dependency:** `tests/pyproject.toml` lists `python-docx` twice.

## Decision

1. **Single source of version truth.** Keep the version in `pyproject.toml` and
   read it at runtime via `importlib.metadata.version("centrifugal-pump")`, or at
   minimum sync `pump.__version__` to match. Pick one scheme and document it.
2. **Declare the UI dependencies.** Add an optional extra so the GUI is
   installable explicitly:
   ```toml
   [project.optional-dependencies]
   gui = ["PySide6", "matplotlib", "numpy"]
   ```
   Then `pip install -e .[gui]` provisions the workbench.
3. **De-duplicate** the `python-docx` entry in `tests/pyproject.toml` (and
   consider whether the separate `tests/pyproject.toml` is needed at all).

## Consequences

**Positive**
- `pip install centrifugal-pump[gui]` becomes the documented one-liner.
- No more "which version is this?" ambiguity.
- Cleaner, DRY packaging metadata.

**Negative**
- Minor: declaring PySide6 as an extra (not a core dep) keeps the library install
  lightweight, but users must remember the `[gui]` extra — documented in the
  tutorial and README.
