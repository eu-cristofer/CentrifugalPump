# Sprint 13 — UC-10 Educational mode + a worked notebook per use case

## Goal
- Every use case, UC-00 to UC-11, has an executable worked notebook that runs green in CI.
- Concept pages explain the physics behind each node.
- The Explorer can show the governing formula in context.

## Files
- `use_cases/`, following the conventions in `use_cases/README.md` and the existing UC-00/UC-06 notebooks:
  - add `UC-01_selection.ipynb`, `UC-02_performance_verification.ipynb` (B-34004A, native units), `UC-03-04_system_operating_point.ipynb`, `UC-05_npsh.ipynb`, `UC-07_trim.ipynb`, `UC-08_compare.ipynb`, `UC-09_reports.ipynb` (docx/tex/pdf in en/pt), `UC-11_mechanical_run.ipynb` and `viscosity_HI967.ipynb`;
  - each notebook uses **only the public `pump` API** with Pint quantities in the engineer's units, and ends with assertions (demo → assertion, the project's example-driven convention).
- `docs/concepts/` (new; linked from the Sphinx toctree in `docs/index.rst`):
  - `affinity.md`, `head-components.md`, `npsh.md`, `viscosity.md`, `acceptance-tolerances.md` (explains data-driven tables and `verified`), `system-curve.md`, `mechanical-run.md`;
  - each page has formulas, units, assumptions, a link to its notebook and a link to the API docs.
- `pumpflow/nodes/explore_plot.py` and the node dialogs: an "ⓘ formula" tooltip or button per derived quantity (head components, affinity, η, NPSHa, B parameter), with text sourced from a single `pumpflow/explain.py` dictionary.
- `tests/test_notebooks.py`:
  - execute every `use_cases/*.ipynb` with `nbclient`, or `nbval` if already available;
  - mark the tests `slow` and skip them when Jupyter is not installed;
  - add `nbclient` to the `[dev]` extra.
- `docs/product/use-cases.md`: UC-10 status 🟡 → ✅ (scope: concepts + notebooks + formula tooltips).

## Reuse
- Existing `use_cases/` notebooks and README rules.
- `docs/conf.py` with myst-parser (already configured).
- `pumpflow/nodes/markdown_note.py` for in-canvas explanations.

## Tests
- `pytest -m slow tests/test_notebooks.py`: every notebook executes without error and its assertions hold.
- Sphinx build: `sphinx-build -b html docs docs/_build/html -W` (warnings as errors) succeeds.

## Acceptance
```bash
pytest
pytest -m slow tests/test_notebooks.py
sphinx-build -b html docs docs/_build/html -W
```

## Definition of done
- 12 worked notebooks; concept pages published; UC-10 ✅.
- Changelog bullet; tracker ticked; one commit.

## Assumes
Sprints 1–12 are done: all use-case APIs exist.
