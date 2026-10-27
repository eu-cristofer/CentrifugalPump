# Sprint S3 — GUI-openable case + persistence guard (8 h)

- **Goal:** Ship a sample `.pumpflow` project the workbench can open via File ▸ Open,
  generated from the real serializer and guarded by a round-trip test.
- **Persona / UC:** FAT engineer · UC-02 / UC-09 (the workbench demo case).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [x] Add a Qt-free `sample_project_doc()` builder to
  [`pumpflow/sample_data.py`](../../pumpflow/sample_data.py) returning the canonical
  single-pump `{nodes, edges}` doc with each node's full default settings (so it is a
  `to_dict` fixed point) — ~3h
- [x] Write [`tests/test_persistence_roundtrip.py`](../../tests/test_persistence_roundtrip.py):
  Qt-free check that the shipped file equals the builder; Qt-side check that
  `to_dict(load_dict(doc)) == doc` and all 11 edges wire up
  ([`scene.py:161-206`](../../pumpflow/canvas/scene.py#L161-L206)), via
  `QT_QPA_PLATFORM=offscreen` + `pytest.importorskip("PySide6")` — ~3h
- [x] Emit [`examples/sample_project.pumpflow`](../../examples/sample_project.pumpflow)
  from the builder — ~1h
- [x] Verify headless: real `GraphScene` loads 7 nodes / 11 edges; pipeline evaluates
  end-to-end (fit R²=0.9991, compliance correctly flags 1 out-of-tolerance point) — ~1h

## Files touched

- Create: `tests/test_persistence_roundtrip.py`, `examples/sample_project.pumpflow`.

## Acceptance criteria

- Round-trip assertion passes (or skips cleanly when PySide6 is absent).
- `examples/sample_project.pumpflow` opens in the GUI and shows a populated canvas.

## Definition of Done

- [x] Sample file shipped, round-trip-guarded (5 tests, all pass with PySide6),
  headless load verified; committed.

> **Note:** the seeded case intentionally evaluates to a **REJECTED** verdict (one
> measured point falls outside the API 610 band) — it demonstrates the compliance
> machinery actually catching a deviation, not a trivial happy path.
