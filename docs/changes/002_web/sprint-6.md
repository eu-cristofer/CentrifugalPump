# Sprint 6 — Witness forms I: Rated Point, Fluid, Test Points, Correction, Fit, Compliance

## Goal
Double-clicking a witness node opens its form in a side panel (desktop: property
window).  Editing a field updates the node's settings in the document and
re-evaluates; computed values come back from Python.

## Files
- `web/src/forms/FormPanel.tsx` — side panel (full screen under 900 px), title bar,
  close, routing by kind; kinds without a form show "Edit on the desktop app".
- `web/src/forms/fields.tsx` — `UnitField` (number + unit select; unit lists and
  conversions come from Python: add `webapi.unit_menu(dimension)` and
  `webapi.convert(value, from, to, dimension)` in this sprint if needed — no
  conversion factors in TypeScript), `PressureField` (+ g/a), `TextField`, `Select`,
  `Checkbox` (with tick), section headers, info buttons with the `explain.py` text
  (`webapi.explain(key)`).
- `web/src/forms/RatedPointForm.tsx` — Identification (Service, Service TAG,
  Standard / edition, Client overlay, Label on report cover), pump type, rated duty,
  NPSHa, fluid link status (UI_SPEC §5.1, §12).
- `web/src/forms/FluidForm.tsx`.
- `web/src/forms/TestPointsForm.tsx` — pump TAG, pressure reference, optional bench
  geometry (rows disabled until applied), editable grid with per-column units,
  computed Head/η columns read-only (from `node_view`), add/remove/move rows, paste
  from spreadsheet (TSV), decimal comma accepted on input.
- `web/src/forms/CorrectionForm.tsx`, `CurveFitForm.tsx`.
- `web/src/forms/ComplianceForm.tsx` — verdict banner (`verdict_text`), parameter
  table, collapsed "Override acceptance criteria…" with the warning, tolerance rows,
  Reason, reset (UI_SPEC §5.6).
- `pumpflow/webapi.py` — any helper the forms need (`unit_menu`, `convert`,
  `explain`, `standards()` / `clients()` lists), with tests in `tests/test_webapi.py`.

## Reuse
- Desktop dialogs as the field reference: `pumpflow/nodes/rated_point.py`,
  `fluid.py`, `test_points.py`, `correction.py`, `curve_fit.py`, `compliance.py`
  (`create_dialog`); `pumpflow/units.py` (menus, `to_standard`); `pumpflow/explain.py`;
  `pumpflow.binding.available_standards/available_clients/standard_label`.
- Settings keys and codec: `pumpflow/settings_codec.py` (the web writes schema-v2
  settings exactly as `encode` would).

## Tests
- Vitest: editing Q in the Test Points grid changes the document settings and, after
  evaluate (mock), shows the returned Head.
- pytest: for each witness kind, a settings dict edited "the web way" (fixture) decodes
  and evaluates; `unit_menu`/`convert` agree with `pumpflow.units`.
- Parity: P-9001B project with A's rows typed through the form helpers equals the
  committed file's evaluation.

## Acceptance
```bash
pytest -q
npm --prefix web run check && npm --prefix web run parity && npm --prefix web run build
```

## Definition of done
A witness can type B's performance rows in the browser and see Compliance change live,
with the same verdict the desktop shows for the same numbers.

## Assumes
Sprint 5: canvas, store, open/save; `webapi.node_view` for these kinds (sprint 3).
