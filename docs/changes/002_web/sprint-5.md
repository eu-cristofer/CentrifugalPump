# Sprint 5 — Canvas: open, view, wire, save

## Goal
The browser shows a `.pumpflow` project as a node canvas like the desktop, lets the
user move, add, delete and wire nodes, re-evaluates through the worker after every
change, and saves the project back to a `.pumpflow` file that the desktop opens
unchanged.

## Files
- `web/src/canvas/Canvas.tsx` — React Flow canvas; positions from the document's
  `x`/`y`; pan/zoom; fit view on open.
- `web/src/canvas/NodeCard.tsx` — custom node: title bar (source nodes lighter, as
  desktop), glyph, port handles coloured by signal type (`port-*` tokens), status row
  with the state glyph (✓ ! ✗, hollow ring idle) or the verdict pill +
  OVERRIDDEN/PROVISIONAL chips (UI_SPEC §3, §11), zoomed-out overview showing only
  title + big verdict below 75 % zoom.
- `web/src/canvas/Toolbox.tsx` — grouped node list from `catalog()` (UI_SPEC §12),
  click to add at the view centre with `default_settings(kind)`.
- `web/src/project/store.ts` — the project document (schema v2) as the single
  state; edits produce a new document; debounced `evaluate(doc)` (150 ms); undo/redo
  (document snapshots, Ctrl/Cmd+Z).
- `web/src/project/files.ts` — open (file input / drag-and-drop) and save
  (download `name.pumpflow`; File System Access API when available).  Unsaved-changes
  guard on close.
- Edge rules: only matching signal types connect (types from `catalog()`); single-
  input ports replace their edge.
- Tests (Vitest + React Testing Library).

## Reuse
- `web/src/engine/client.ts`, `types.ts` (sprint 4); `catalog()`, `evaluate()`,
  `default_settings()`; `tokens.css`.
- Desktop look: `pumpflow/canvas/node_item.py` (`_paint_pill`, `_STATE_GLYPH`,
  `_status_beside`, `LOW_DETAIL_LOD`) as the visual reference; `docs/UI_SPEC.md`
  §3, §11, §12.

## Tests
- Store: open → save returns a document equal (deep) to the input for the P-9001A
  and P-9001B projects except `view`.
- Wiring a TestPointSet output into a RatedPoint input is refused.
- NodeCard renders `APPROVED ✓` pill for a compliance node view, and ✓/!/✗ glyphs.
- Python side (pytest): a document saved by the web store (fixture JSON produced by
  the Vitest run and committed as `tests/fixtures/web/saved_p9001a.pumpflow`) loads
  in `Graph` and gives the same statuses.

## Acceptance
```bash
pytest -q
npm --prefix web run check && npm --prefix web run parity && npm --prefix web run build
```

## Definition of done
P-9001A opens, looks like the desktop canvas (pills, glyphs, groups), can be
re-wired and saved; the desktop opens the saved file with identical statuses.

## Assumes
Sprint 4: worker, client, types, tokens.css, parity script.
