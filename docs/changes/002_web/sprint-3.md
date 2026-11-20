# Sprint 3 — JSON API for the browser (`pumpflow.webapi`)

## Goal
One plain-JSON boundary between Python and the web front end.  Everything the
browser shows comes from here; the browser never computes.

## Files
- `pumpflow/webapi.py` (new), all functions take/return JSON-serialisable values
  (str/float/int/bool/None/list/dict; quantities as `{"value", "unit"}` via
  `pump.quantity_io.to_json`; NaN/inf → `None`):
  - `catalog() -> list` — node kinds: kind, title, glyph, group (from
    `registry.grouped_node_kinds`), input/output port names and signal type names,
    `has_web_form` (true for the witness kinds listed in the project README).
  - `evaluate(doc: dict) -> dict` — `Graph.from_dict(doc)`, evaluate, return
    `{"nodes": {id: {"kind", "state", "status", "badge": [text, tone] | None,
    "notes": [...], "view": {...}}}, "errors": [...]}`.
  - `node_view(node) -> dict` — per-kind display data for the witness kinds, built
    from the node's `outputs_cache` and settings, e.g.:
    - test_points: per-row computed head / efficiency (display units of the node);
    - correction / curve_fit: corrected points and fitted curve series
      (`q`, `head`, `power`, `eff` arrays, R²);
    - compliance: the parameter rows (name, actual, predicted, min, max, deviation,
      tol, verdict, note), `verdict_text`, overridden/unverified;
    - npsh: NPSHr series, NPSHa, margin, ratio, verdict;
    - mechanical_run_check: per-check rows and verdict;
    - performance_plot: series for head/power/eff/NPSH + rated point.
    Unknown kinds return `{}`.
  - `default_settings(kind: str) -> dict` — encoded (schema v2) settings of a fresh node.
  - `export_report(doc: dict, fmt: str, lang: str | None = None) -> dict` —
    `{"filename", "mime", "base64"}` for `docx`, `html`, and `xlsx` test summary
    (`summary_xlsx`); `tex`/`pdf` raise `ValueError("desktop only")`.  Writes into a
    `tempfile.TemporaryDirectory`.
- `tests/test_webapi.py` (new).

## Reuse
- `pumpflow.engine.Graph`; `pumpflow/export_cli.py` `report_inputs`,
  `report_notes`; `pumpflow.binding` `assemble_report_data`, `export_reports`,
  `generate_html`, `test_data_summaries`, `export_test_summary`;
  `pumpflow.signals.ComplianceResult.verdict_text`; `pump.quantity_io.to_json`;
  `pumpflow.nodes.registry.grouped_node_kinds`.

## Tests
- `json.dumps(evaluate(doc), allow_nan=False)` succeeds for every
  `tests/fixtures/v1/*.pumpflow` and the B-34004A/B projects.
- `evaluate` states/statuses equal `expected.json` (same helper as sprint 1).
- B-34004A compliance view: `verdict_text == "APPROVED ✓"`, Head row predicted
  within 0.01 of the desktop `ComplianceResult` value.
- `export_report(doc, "docx")` → base64 decodes to a zip starting `PK`;
  `"html"` contains the tag; `"pdf"` raises `ValueError`.
- `catalog()` covers all 18 kinds; `has_web_form` true exactly for the 12 witness kinds.
- `default_settings` round-trips through `settings_codec.decode`/`encode`.

## Acceptance
```bash
pytest -q
black --check pumpflow/webapi.py tests/test_webapi.py
```

## Definition of done
A documented, tested JSON API; module docstring lists every function and its payload
shape (this is the contract the TypeScript types in sprint 4 mirror).

## Assumes
Sprints 1–2: `Graph` exists and the engine path imports without Qt.
