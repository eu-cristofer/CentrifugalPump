# Sprint 14 — Masterpiece polish: report, CI, docs

## Goal
- The deliverable a FAT witness signs:
  - one consolidated report, identical in content across docx, tex, pdf and html, in en and pt;
  - a cover page, every section from the project, deviations and open points, and a signature block.
- Quality gates in CI.
- Docs and registry complete.

## Files
- Reports (`pump/utilities/report.py`, `report_latex.py`, new `report_html.py`):
  - cover page: project, client, service/tag(s), standard and edition (S5), test date and location, revision;
  - sections, in order:
    1. equipment;
    2. rated data;
    3. performance per unit;
    4. comparison (S7);
    5. NPSH (S8);
    6. mechanical run (S6);
    7. viscosity factors (S9) when applied;
    8. deviations, unverified criteria and open points (from Markdown note nodes tagged `report: true`);
    9. signature block (vendor, inspector, client witness).
  - HTML export: a self-contained single file (inline PNGs as data URIs).
  - `binding.export_reports` gains the `"html"` format, and the GUI "Export all" includes it.
  - Report Export node: new fields for project, client, test date, location, revision and signatories (v2 settings).
  - `.po` en/pt updated.
- `.github/workflows/ci.yml` (new):
  - matrix Python 3.12 and 3.13 (`requires-python = ">=3.12"`);
  - `pip install -e ".[dev,gui]"`;
  - `QT_QPA_PLATFORM=offscreen pytest`;
  - `black --check` on the black-clean file set (list it in `pyproject.toml` `[tool.black] include` or run on the explicit paths);
  - `mypy pump` (add `mypy` to `[dev]`; start with `--ignore-missing-imports` and fix the errors in `pump/`);
  - an optional LaTeX job (`texlive` action) that compiles the P-9001A PDF via `python -m pumpflow.export_cli … --formats pdf`.
- Docs:
  - `README.md` roadmap section: replace it with a "Capabilities" table that links each UC notebook;
  - `docs/UI_SPEC.md`: add the new nodes (mechanical_run, compare, npsh, trim, system_curve, operating_point, selection) and schema v2;
  - `docs/multi-unit-philosophy.md`: Pint end to end, value+unit persistence, migration;
  - ADRs touched by this project (0002, 0009, plus a new **ADR-0011 schema v2 value+unit persistence**) set to Accepted;
  - `docs/product/use-cases.md`: every UC ✅.
- `docs/changes/001_masterpiece/README.md`: `Status: ready to archive`.

## Reuse
- `binding.assemble_report_data` and `export_reports`.
- `LatexReportGenerator` and `ReportGenerator`, sharing the prose constants in `pump/utilities/report.py`.
- `pumpflow/export_cli.py`.

## Tests
- `tests/test_report_formats.py`:
  - html export is a single file with embedded images;
  - every section heading appears in docx, tex and html when its data is present, and is absent otherwise;
  - cover fields are rendered;
  - pt translations for every new heading.
- CI green on a pushed branch: run the workflow via `gh workflow run` or by pushing `feat/masterpiece`, but **only after the owner approves pushing**.
- Final end-to-end:
  1. Copy P-9001A into a P-9001B witness file and fill branch B in memory with synthetic but plausible readings, inside the test only.
  2. Export docx, tex, pdf and html in en and pt.
  3. Rasterise the PDF with `gs` and inspect the cover, the comparison and the mechanical run.

## Acceptance
```bash
pytest
QT_QPA_PLATFORM=offscreen pytest tests/test_persistence_roundtrip.py
mypy pump
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/p9001 --formats docx,tex,pdf,html --lang pt
sphinx-build -b html docs docs/_build/html -W
```

## Definition of done
- All four formats in both languages.
- CI workflow committed (and green, if push was approved).
- Registry all ✅; ADR-0011 written.
- Project marked `Status: ready to archive`.
- Changelog bullet; tracker ticked; one commit.

## Assumes
Sprints 1–13 are done.
