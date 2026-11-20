# Sprint 2 — Node logic importable without Qt

## Goal
`import pumpflow.engine` and `pumpflow.nodes.registry` must work in an interpreter
where PySide6 and pyqtgraph do not exist (Pyodide).  Qt is only needed when a dialog
is built.

## Files
- Every `pumpflow/nodes/*.py` that imports `PySide6`, `pyqtgraph`, `.ui`, `.plotting`,
  `..style` or `..canvas` at module level: move those imports inside
  `create_dialog` (or into Qt-only helpers called from it).  Module-level helpers that
  only exist for dialogs (e.g. `test_points._set_ro`) move into the dialog code path or
  a `_dialog` helper that imports Qt lazily.
- `pumpflow/nodes/ui.py`, `plotting.py`, `canvas/`, `app.py`, `welcome.py`, `style.py`
  stay Qt modules (not imported by the engine path).
- `pumpflow/binding/*`: check nothing imports Qt (should already be true).
- `tests/test_qt_free_engine.py` (new).

## Reuse
- Module list from `pumpflow/nodes/registry.py` `_CLASSES`.
- Existing GUI tests (`tests/test_*_gui.py`) prove dialogs still build.

## Tests
- In a **subprocess** (so the running test session's Qt is not affected), run Python
  with a meta-path finder that raises `ImportError` for `PySide6`, `shiboken6` and
  `pyqtgraph`, then: `from pumpflow.engine import Graph`; load and evaluate
  `examples/user/B-34004A_MRT_reference.pumpflow`; print node states as JSON; assert
  they equal the statuses from an in-process `Graph` run.
- Same subprocess: `from pumpflow import binding` and `assemble_report_data` +
  `generate_html` to a temp file succeed (matplotlib with the Agg backend).
- Static guard: parse each `pumpflow/nodes/*.py` (except `ui.py`, `plotting.py`,
  `test_points` widget helpers if separated) with `ast` and assert no module-level
  import of `PySide6`/`pyqtgraph`/`.ui`/`.plotting`.

## Acceptance
```bash
pytest -q
black --check tests/test_qt_free_engine.py
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
The engine path is Qt-free and guarded by a test; every dialog still opens (GUI tests
green); no behaviour change.

## Assumes
Sprint 1: `pumpflow/engine.py` with `Graph.from_dict/evaluate` exists.
