# Sprint S4 — Docstrings & doctests (8 h)

- **Goal:** Make the docstring examples correct and *executable*, so documentation
  can never silently rot.
- **Persona / UC:** all personas (documentation quality).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [x] Fix wrong/unrunnable examples: bare `from utilities …` / `from unit_conversion …`
  imports → `from pump.utilities …`; stale `density=1.0` and `…/second` outputs; the
  `PumpPerformanceCurve` NameError; `BasePoint` import error — ~2.5h
- [x] Add runnable, deterministic `>>>` examples to the core public classes
  (`BasePoint`, `TestPoint`, `DesignPoint`, `PerformanceCurve`, `PerformanceChecker`)
  — ~3.5h
- [x] Wire `--doctest-modules` into `[tool.pytest.ini_options]`
  (`testpaths = ["tests", "pump"]`); make it green (**7 doctests, 46 total**) — ~2h

> **Note:** the lower-level helper symbols (e.g. `ImprovedQuantity`, `PerformanceFitter`,
> report internals) still rely on module-level prose rather than per-symbol `>>>`
> examples — a low-priority follow-on; the MVP public surface (UC-02/UC-06) is fully
> exemplified and doctested.

## Files touched

- Modify: `pump/utilities/fluid.py`, `pump/utilities/unit_conversion.py`,
  and other `pump/` modules as needed; `pyproject.toml` (doctest config).

## Acceptance criteria

- `pytest --doctest-modules pump` passes.
- No `__all__` symbol lacks a docstring example.

## Definition of Done

- [x] Doctests green and wired into the suite (46 passed); committed.
