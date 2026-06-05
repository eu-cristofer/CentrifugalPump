# Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)

- **Goal:** Publish an auto-generated API reference + the existing prose on Read the
  Docs, built cleanly from the docstrings.
- **Persona / UC:** all personas (discoverability).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [x] Add a `docs` extra to [`pyproject.toml`](../../pyproject.toml): `sphinx`, `furo`,
  `myst-parser`, `sphinx-autodoc-typehints`, `sphinxcontrib-mermaid` — ~0.5h
- [x] Create `docs/conf.py` (autodoc + autosummary + napoleon + myst_parser +
  mermaid; `autodoc_mock_imports=["PySide6"]`) and `docs/index.rst` + `docs/overview.md` — ~2.5h
- [x] Create `docs/api/pump.rst` + `docs/api/pumpflow.rst` (automodule over the public
  modules; Qt nodes documented from source under the mock) — ~2h
- [x] `myst-parser` embeds existing [ARCHITECTURE.md](../ARCHITECTURE.md),
  [RUN_AND_TEST.md](../RUN_AND_TEST.md), ADRs, sprints, and product docs via toctrees;
  `myst_fence_as_directive=["mermaid"]` renders the diagrams — ~1.5h
- [x] Add `.readthedocs.yaml` (Py 3.12, `install .[docs]`); build green — ~1.5h

## Files touched

- Modify: `pyproject.toml`.
- Create: `docs/conf.py`, `docs/index.rst`, `docs/api/*`, `.readthedocs.yaml`.

## Acceptance criteria

- `pip install -e .[docs]` && `sphinx-build -b html docs docs/_build/html` builds with
  no autodoc import errors.
- API pages for `pump` + `pumpflow` are generated from docstrings.

## Definition of Done

- [x] Clean local Sphinx build (exit 0; only 2 warnings, both intersphinx inventory
  fetches that fail offline and resolve on RTD); API pages for `pump` + `pumpflow`
  generated from docstrings; RTD-ready config committed.
