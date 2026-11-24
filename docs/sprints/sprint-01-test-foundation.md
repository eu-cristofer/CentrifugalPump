# Sprint S1 — Test foundation + units spec (8 h)

- **Goal:** Turn the units/`Fluid` demo notebook into a green, asserted pytest suite
  and fix the broken test-config foundation.
- **Persona / UC:** FAT engineer · UC-02 (foundation — units consistency underpins
  every compliance verdict).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [x] Delete the stray [`tests/pyproject.toml`](../../tests/pyproject.toml) (a duplicate
  of the root, repeats `python-docx` twice) — ~0.5h
- [x] Add `[tool.pytest.ini_options]` to the **root**
  [`pyproject.toml`](../../pyproject.toml): `testpaths`, `addopts` — ~1h
- [x] Add [`tests/conftest.py`](../../tests/conftest.py) hoisting the `water` / `curve` /
  `design_point` fixtures; de-dup the smoke file — ~2h
- [x] Mark domain `TestPoint.__test__ = False` so pytest stops collecting it
  ([`pump/point.py`](../../pump/point.py)) — ~0.5h
- [x] Write [`tests/test_utilities.py`](../../tests/test_utilities.py) — assert every
  printed line of the notebook + contract edge cases (bad context / non-`Quantity`
  → `ValueError`; unknown dimensionality → `pytest.warns`) — ~3.5h
- [x] `pytest -v`; capture green output (**20 passed**) — ~0.5h

## Files touched

- Modify: `pyproject.toml`, `tests/test_pump_smoke.py`.
- Delete: `tests/pyproject.toml`.
- Create: `tests/conftest.py`, `tests/test_utilities.py`.

## Acceptance criteria

- One `pyproject.toml` in the repo; `pytest` is configured there.
- `tests/test_utilities.py` pins: `500 g→0.5 kg`, `1 atm→101325 Pa`, `delta→1.01325 bar`,
  `1 degC delta→1.0 K`, `Fluid` density canonicalized to `kg/m**3`.
- `pytest -v` is fully green (existing smoke + new utilities tests).

## Definition of Done

- [x] Suite green (20 passed); notebook behaviour is now an executable spec; committed.
