# Sprint 1 — Anonymiser and leak scanner

## Goal
Two small, tested tools that later sprints run: one rewrites names and tags from a
private map without touching numbers; the other finds any confidential word in files,
archives or outgoing commits.

## Files
- `tools/anonymise.py` — `python tools/anonymise.py --map MAP.yaml PATH... [--rename] [--check]`.
  - Map format (YAML): `replace: {"real string": "public string", ...}` and
    `rename: {"real/path": "public/path", ...}`.  Longest keys replaced first;
    case-sensitive by default, with an optional `ignore_case: [...]` list.
  - Rewrites text files (`.pumpflow`, `.json`, `.ipynb`, `.md`, `.rst`, `.py`, `.ts`,
    `.tsx`, `.toml`, `.yml`, `.txt`, `.csv`) in place.  `.ipynb`: also in outputs.
  - Never rewrites digits: a replacement whose key is purely numeric is refused.
  - `--check` prints what would change and exits 1 if anything would.
- `tools/leak_scan.py` — `python tools/leak_scan.py --words WORDLIST [PATH...] [--git-range A..B]`.
  - Word list: one entry per line, `#` comments.  Matching is case-insensitive and also
    matches the entry with `-`, `_`, `.` and spaces removed (e.g. a tag written without
    its hyphen).
  - Scans text files, and the XML inside zip containers (`.docx`, `.xlsx`, `.pptx`) and
    `.ipynb` outputs; reports `path:line: entry` (never prints more than the entry).
  - `--git-range` scans added lines, file names and commit messages of the range.
  - Exit 1 on any hit, 0 when clean.
- `tests/test_anonymise.py`, `tests/test_leak_scan.py` — toy map and word list only.
- `.github/workflows/ci.yml` — add the two tools and tests to the black list.
- `pyproject.toml` — add `pyyaml` to `[dev]` if not already available.

## Reuse
- `pumpflow.engine` (`Graph`, `evaluate_in_order`) and `pumpflow.webapi.evaluate` for the
  verdict-equality test; `pumpflow.persistence` to load `.pumpflow`.
- `tests/fixtures/v1/expected.json` and its existing status-pinning test pattern
  (`tests/test_persistence_roundtrip.py` / the v1 fixture tests).

## Tests
- Anonymise a copy of the current regression fixture (`tests/fixtures/v1/`, the MRT
  reference) with a toy map that renames its tag and vendor: every number in the JSON is
  byte-identical, and `webapi.evaluate` statuses/verdicts equal those of the original.
- Numeric-only map key is refused; longest-key-first ordering; `--check` exit codes;
  `.ipynb` outputs rewritten.
- Leak scan: hit in text, in a `.docx` (build one with python-docx in a tmp dir), in a
  hyphen-less spelling, in a git range (tmp repo), in a commit message; clean tree → 0.

## Acceptance
```bash
pytest -q tests/test_anonymise.py tests/test_leak_scan.py
pytest -q
black --check tools/anonymise.py tools/leak_scan.py tests/test_anonymise.py tests/test_leak_scan.py
```

## Definition of done
Both tools work from the command line on the toy inputs; no real name appears in any
new file.

## Assumes
`feat/public-split` branched from `main` at `128bf22` (002_web complete); `pumpflow.webapi`
and `pumpflow.engine` as delivered by 002_web.
