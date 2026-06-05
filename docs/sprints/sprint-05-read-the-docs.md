# Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)

- **Goal:** Publish an auto-generated API reference + the existing prose on Read the
  Docs, built cleanly from the docstrings.
- **Persona / UC:** all personas (discoverability).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [ ] Add a `docs` extra to [`pyproject.toml`](../../pyproject.toml): `sphinx`, `furo`,
  `myst-parser`, `sphinx-autodoc-typehints` — ~0.5h
- [ ] Create `docs/conf.py` (autodoc + autosummary + napoleon + myst_parser),
  `docs/index.rst` — ~2.5h
- [ ] Create `docs/api/` autosummary stubs for `pump` + `pumpflow` — ~2h
- [ ] `myst-parser` embeds existing [ARCHITECTURE.md](../ARCHITECTURE.md),
  [RUN_AND_TEST.md](../RUN_AND_TEST.md), ADRs, and the new product docs — ~1.5h
- [ ] Add `.readthedocs.yaml` (Py 3.12, `install .[docs]`); build with
  `sphinx-build -b html docs docs/_build/html`; report warnings — ~1.5h

## Files touched

- Modify: `pyproject.toml`.
- Create: `docs/conf.py`, `docs/index.rst`, `docs/api/*`, `.readthedocs.yaml`.

## Acceptance criteria

- `pip install -e .[docs]` && `sphinx-build -b html docs docs/_build/html` builds with
  no autodoc import errors.
- API pages for `pump` + `pumpflow` are generated from docstrings.

## Definition of Done

- [ ] Clean local Sphinx build; RTD-ready config committed.
