# Sprint S3 — GUI-openable case + persistence guard (8 h)

- **Goal:** Ship a sample `.pumpflow` project the workbench can open via File ▸ Open,
  generated from the real serializer and guarded by a round-trip test.
- **Persona / UC:** FAT engineer · UC-02 / UC-09 (the workbench demo case).
- **Branch / commit:** `orange` — one commit.

## Tasks (≈ 8 h)

- [ ] Write [`tests/test_persistence_roundtrip.py`](../../tests/test_persistence_roundtrip.py) —
  build the canonical graph via [`pumpflow/sample_data.py`](../../pumpflow/sample_data.py),
  assert `to_dict(load_dict(doc)) == doc`
  ([`scene.py:161-206`](../../pumpflow/canvas/scene.py#L161-L206)); run with
  `QT_QPA_PLATFORM=offscreen`, `pytest.importorskip("PySide6")` — ~4h
- [ ] Emit [`examples/sample_project.pumpflow`](../../examples/) from that same
  `scene.to_dict()` output (never hand-author serialization) — ~2.5h
- [ ] Manual check: `python -m pumpflow` → File ▸ Open
  ([`app.py:207`](../../pumpflow/app.py#L207)) → sample loads a populated canvas — ~1.5h

## Files touched

- Create: `tests/test_persistence_roundtrip.py`, `examples/sample_project.pumpflow`.

## Acceptance criteria

- Round-trip assertion passes (or skips cleanly when PySide6 is absent).
- `examples/sample_project.pumpflow` opens in the GUI and shows a populated canvas.

## Definition of Done

- [ ] Sample file shipped, round-trip-guarded, manually verified; committed.
