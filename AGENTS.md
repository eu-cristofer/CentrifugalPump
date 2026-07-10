## Fast Orientation

- Two packages ship from this repo: `pump/` (headless physics library) and `pumpflow/` (PySide6 GUI workbench that orchestrates the library).
- Python floor is 3.12 (`pyproject.toml: requires-python = ">=3.12"`).

## Commands (Match Repo Config)

- Dev install (library + pytest/black/build): `pip install -e ".[dev]"`
- Run full test suite: `pytest`
- Run one file: `pytest tests/test_utilities.py`
- Run one test: `pytest tests/test_affinity.py::test_to_speed_round_trip_is_identity`
- GUI deps (for `python -m pumpflow`): `pip install -e ".[gui]"` (or `pip install PySide6 matplotlib numpy pyqtgraph`)
- Launch GUI: `python -m pumpflow`
- Build docs (Sphinx): `pip install -e ".[docs]" && sphinx-build -b html docs docs/_build/html`
- Conda env is optional: `mamba env create -f environment.yml && mamba activate pump` (channels intentionally live in `.condarc`, not `environment.yml`).

## Testing Gotchas

- Pytest is configured to collect `tests/` plus doctests in `pump/` only (`pyproject.toml: testpaths = ["tests", "pump"], addopts includes `--doctest-modules`).
- `pumpflow/` is deliberately excluded so headless test runs do not require PySide6; don’t “fix” discovery by making GUI modules look less like tests.
- GUI round-trip tests skip when PySide6 is missing and set `QT_QPA_PLATFORM=offscreen` when present (see `tests/test_persistence_roundtrip.py`).

## Hard Boundary

- `pumpflow/binding.py` is intended to be the only place the GUI calls into `pump`. Don’t import `pump` from random `pumpflow/nodes/*` modules.

## Units/System Conventions

- Library constructors expect Pint quantities (`pump.Q_`), not raw numbers.
- Unit canonicalization is centralized in `pump.utilities.unit_conversion.quantity_factory`.
- Attribute naming can route unit conversion context (e.g. `atm`/`delta` prefixes are meaningful); avoid those prefixes unless intended.

## Reports / Localization

- `.docx` output uses `pump.ReportGenerator` and templates in `pump/templates/template_{en,pt}.docx`.
- If you change report strings/templates, update `.po` files and recompile PT to `.mo`:
  `msgfmt pump/utilities/locales/pt/LC_MESSAGES/messages.po -o pump/utilities/locales/pt/LC_MESSAGES/messages.mo`

## Persistence Guard

- The shipped demo file `examples/sample_project.pumpflow` is pinned to a builder function. Regenerate via the command embedded in `tests/test_persistence_roundtrip.py` (don’t hand-edit the JSON).

## Repo Noise

- `sample_repo/` is third-party/example material and is not part of this project’s packaging/test flow.

## graphify

- Only use graphify when `graphify-out/graph.json` exists. Prefer `graphify query "<question>"`, then `graphify path` / `graphify explain` over raw greps.
- Dirty `graphify-out/` files are expected after updates; don’t treat them as a reason to stop.
- After modifying code, run `graphify update .` to keep the local graph current.
