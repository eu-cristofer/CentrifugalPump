# Sprint S4 — Docstrings & doctests (8 h)

- **Goal:** Make the docstring examples correct and *executable*, so documentation
  can never silently rot.
- **Persona / UC:** all personas (documentation quality).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [ ] Fix wrong examples: [`fluid.py`](../../pump/utilities/fluid.py) header shows
  `1.0 kg/m**3` for a `1000 kg/m**3` input; `unit_conversion.py` doctests use
  unresolvable bare `from unit_conversion import …` — ~2.5h
- [ ] Ensure every symbol in each `__all__` has a one-line summary + one runnable
  `>>>` example — ~3.5h
- [ ] Wire `pytest --doctest-modules pump` into the suite/config; make it green — ~2h

## Files touched

- Modify: `pump/utilities/fluid.py`, `pump/utilities/unit_conversion.py`,
  and other `pump/` modules as needed; `pyproject.toml` (doctest config).

## Acceptance criteria

- `pytest --doctest-modules pump` passes.
- No `__all__` symbol lacks a docstring example.

## Definition of Done

- [ ] Doctests green and wired into the suite; committed.
