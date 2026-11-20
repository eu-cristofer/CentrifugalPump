# Sprint 1 — Headless graph engine

## Goal
Move graph evaluation out of the Qt `GraphScene` into a Qt-free
`pumpflow/engine.py`, shared by the desktop canvas, the export CLI and (later) the
browser.  Behaviour is unchanged: same topological order, same input gathering,
same error capture, same statuses.

## Files
- `pumpflow/engine.py` (new): `class Graph`
  - `nodes: list[BaseNode]` (insertion order), `edges: list[Edge]` with
    `Edge(src_node, src_port, dst_node, dst_port)` (frozen dataclass of ids/names);
  - `add_node(kind, node_id=None, settings=None) -> BaseNode` (uses
    `registry.make_node`), `connect(src_id, src_port, dst_id, dst_port)` (validates
    the ports exist on the node specs, ignores duplicates), `remove_node`, `disconnect`;
  - `topo_order() -> list[BaseNode]` (Kahn, stable by insertion index; cycle leftovers
    appended — identical to `GraphScene._topo_order`);
  - `gather_inputs(node) -> dict[str, list]` (identical to `GraphScene._gather_inputs`);
  - `evaluate()` (run each node in order; exceptions → `node.set_error(str(exc))`);
  - `@classmethod from_dict(doc)` (`persistence.migrate`, `units.PREFS.load(meta)`,
    `settings_codec.decode`, node positions kept in a `positions: dict[id, (x, y)]`)
    and `to_dict(view=None)` producing the exact schema-v2 document `GraphScene.to_dict`
    produces (meta, nodes with x/y and encoded settings, edges).
- `pumpflow/canvas/scene.py`: keep the public API, but delegate `_topo_order`,
  `_gather_inputs` and `evaluate` to logic shared with `engine.py` (a helper
  function taking `(nodes, edges)` ids is fine), so there is one implementation.
- `pumpflow/export_cli.py`: `build_scene` → `build_graph(project)` using `Graph`; no
  `QApplication` needed.  `report_inputs` / `report_notes` take the graph.  Keep a
  `build_scene` alias only if a test imports it.
- `tests/test_engine.py` (new).

## Reuse
- `pumpflow/canvas/scene.py` `_topo_order`, `_gather_inputs`, `evaluate`, `to_dict`,
  `load_dict` — the reference behaviour.
- `pumpflow/persistence.py` `migrate`, `read_json`; `pumpflow/settings_codec.py`
  `encode`/`decode`; `pumpflow/units.py` `PREFS`; `pumpflow/nodes/registry.py`
  `make_node`; `pumpflow/nodes/base.py` `BaseNode.run/set_error/outputs_cache`.

## Tests
- For every `tests/fixtures/v1/*.pumpflow`: `Graph.from_dict(read_json(f))` +
  `evaluate()` gives the same `[kind, state, status]` per node as
  `tests/fixtures/v1/expected.json` (reuse `_summary` logic from
  `tests/test_schema_migration.py`, including compliance rows).
- `Graph.to_dict()` of a loaded fixture equals `GraphScene.to_dict()` of the same
  fixture (offscreen Qt; skip if PySide6 missing).
- Cycle: two nodes wired in a loop still evaluate (leftovers appended), no exception.
- `connect` with an unknown port raises `ValueError`.
- export_cli runs on B-34004A with `QT_QPA_PLATFORM` unset and no `QApplication`
  created (assert `QApplication.instance() is None` after `build_graph`).

## Acceptance
```bash
pytest -q
black --check pumpflow/engine.py tests/test_engine.py
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
One graph-evaluation implementation; desktop, CLI and tests use it; fixture statuses
unchanged; `tests/test_engine.py` added to the CI black list.

## Assumes
`GraphScene` evaluates via `_topo_order` / `_gather_inputs` / `evaluate`
(`pumpflow/canvas/scene.py`); `export_cli.build_scene` loads through `GraphScene`.
