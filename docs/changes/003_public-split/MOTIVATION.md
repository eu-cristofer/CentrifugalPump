# 003_public-split — Motivation

## Problem

The GitHub repo was meant to be private but showed as **public** on 2026-11-23.  It
holds customer material: real witness projects, vendor names, plant tags, document
numbers and real reports.  Its history cannot be cleaned safely.  At the same time the
owner wants the code, the documentation and the web app to be public.

## Approach

- **Two repos with different jobs, not two copies of the code.**  The public repo holds
  all the code and anonymised examples; the private data repo holds only customer files.
  Nothing is synced between them, so there is no sync to leak through.
- **Anonymise by mapping strings.**  Company names → "Vendor A/B…", tags and document
  numbers → `P-9xxx`; numbers untouched, so the anonymised regression fixture gives the
  same verdicts as the real one.  The map lives only in the data repo.
- **Guard every push.**  A scanner with a private word list runs as a pre-push hook and
  as a CI job (word list as a repository secret).
- **Fresh history.**  The public repo starts from one commit of the clean tree; today's
  repo becomes `CentrifugalPump-archive` (private, frozen).
- **Publish from `main`.**  GitHub Pages serves the Sphinx docs at the site root and the
  web app under `/app/`.

## How changes are handled afterwards

- Every code change (library, desktop, web, docs) is a branch + PR + merge in the public
  repo.  CI re-vendors the wheel and runs `parity`, so the web follows the desktop; Pages
  redeploys on merge.
- Real cases are opened from `../CentrifugalPump-data/` (desktop or the web Open button)
  and saved there; that repo is committed separately.
- `CentrifugalPump-data/check.sh` runs the public `export_cli` on the real projects and
  compares statuses with privately stored expectations: run it before merging a change
  that can move a verdict.

## Decisions

- 2026-11-23 — every real tag, vendor and report is confidential; numbers stay untouched.
- 2026-11-23 — "Petrobras N-553" stays public (a standard name, cited by clause only).
- 2026-11-23 — repo names: `CentrifugalPump-archive` (private, frozen, today's repo),
  `CentrifugalPump` (public, new), `CentrifugalPump-data` (private).
- 2026-11-23 — hosting for 002_web: GitHub Pages, docs at the root, app at `/app/`;
  Read the Docs dropped.

## Risks

- **A name slips through** (a filename, notebook output, docx metadata, graphify output,
  a commit message).  Mitigated by the scanner over files *and* the snapshot, scanning
  binary/zip contents (docx, xlsx) as text, and a fresh single-commit history.
- **Names drawn in pixels** (a chart title saved in a notebook output) are invisible to
  a text scanner.  Tracked notebooks carry no image outputs (`tests/test_notebook_images.py`).
- **Anonymisation changes a verdict.**  Mitigated by a test that compares statuses
  before/after and by `parity`.
- **The web app under a sub-path** (`/CentrifugalPump/app/`) breaks the worker's `/py/`
  path or the service-worker scope.  Mitigated by a base-path build tested locally under
  the same path.
- **The word list in CI** is a secret; fork PRs do not get it, so the job skips there
  and the pre-push hook remains the first line.
