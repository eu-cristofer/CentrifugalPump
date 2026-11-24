# Sprint 2 — Apply: originals to the data folder, anonymised copies in the repo

## Goal
After this sprint the working tree contains no confidential word, every test and the
web parity gate still pass with the same verdicts, and every original is safe in the
private data folder.

## Files
- **Data folder (outside the repo):** `../CentrifugalPump-data/`, created with `git init`
  (local only, never pushed by this sprint).  It gets:
  - `map.yaml` and `wordlist.txt` — written by the orchestrator from a scan of the tree
    (vendors, customer/plant names, all real tags, document and serial numbers; the
    owner reviews them).  Every real tag maps to a distinct `P-9xxx`; vendors to
    "Vendor A/B…".  "Petrobras N-553" (the standard name) stays public and is not in
    the word list; customer/plant names are.
  - `originals/` — copies of every original before rewriting: the customer PDFs in
    `examples/user/`, `examples/user/*.pumpflow`, the real docx reports in `examples/`,
    the `examples/*.ipynb` with real tags, `examples/catalogue/*` with real tags, and the
    real-named fixtures.
- **Repo:** run `tools/anonymise.py --map ../CentrifugalPump-data/map.yaml --rename` over
  the tracked tree.  This renames the fixtures and examples (the MRT reference fixture
  becomes `P-9001A_MRT_reference.pumpflow`, the web fixture `saved_p9001a.pumpflow`) and
  rewrites references in `tests/`, `use_cases/` (then regenerate the notebooks with
  `python use_cases/build_notebooks.py`), `docs/` (including `docs/changes/*`),
  `web/src`, `web/scripts`, `pumpflow/`, `pump/`, `README.md`, `CLAUDE.md`, `CHANGELOG.md`.
- Real docx reports in `examples/`: removed from the repo (originals kept in the data
  folder), replaced by reports regenerated from the anonymised projects with
  `python -m pumpflow.export_cli`.
- Customer PDFs: moved (not copied) out of `examples/user/`; `examples/user/` keeps only
  anonymised projects.
- `graphify-out/`: removed from git and git-ignored (regenerated locally).
- `tests/fixtures/v1/expected.json`: keys renamed only; statuses unchanged.

## Reuse
- `tools/anonymise.py`, `tools/leak_scan.py` (sprint 1).
- `use_cases/build_notebooks.py`; `pumpflow.export_cli`.

## Tests
- Full `pytest` with the renamed fixtures; the regression fixture exports with the same
  verdicts.
- `npm --prefix web run vendor && npm --prefix web run check && npm --prefix web run parity`.
- `python tools/leak_scan.py --words ../CentrifugalPump-data/wordlist.txt .` → 0 hits
  (tracked files; `git ls-files | xargs` form).

## Acceptance
```bash
pytest -q
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out "$TMPDIR/p9001" --formats docx,html
npm --prefix web run vendor && npm --prefix web run check && npm --prefix web run parity
git ls-files -z | xargs -0 python tools/leak_scan.py --words ../CentrifugalPump-data/wordlist.txt
```

## Definition of done
Leak scan clean over tracked files; tests and parity green; data folder holds every
original plus `map.yaml` and `wordlist.txt`.  Commit message and new file names contain
no real name.

## Assumes
Sprint 1: `tools/anonymise.py` and `tools/leak_scan.py` exist and are tested.
