# Sprint 5 — Cutover kit, data repo skeleton and docs

## Goal
Everything ready for the owner to create the two new repos in a few commands, and the
docs explain the three-repo way of working.

## Files
- `tools/make_public_snapshot.sh DEST` — `git archive HEAD` into an empty `DEST`, run
  `tools/leak_scan.py` over it (abort on any hit), `git init -b main`, one commit
  "Initial public release", install the hooks.  Never pushes.
- **Data folder** `../CentrifugalPump-data/` (local repo from sprint 2) gets:
  - `README.md` — what lives here, how to open a real case with the desktop and the web
    app, how to commit.
  - `expected/` — node statuses and verdicts of every real project, generated now with
    the public code.
  - `check.sh` — runs `python -m pumpflow.export_cli` (from `../CentrifugalPump`) on each
    real project and compares with `expected/`; exits 1 on any difference.
  - organised by project: originals moved from `originals/` into one folder per pump.
- `README.md` and `CLAUDE.md` — new "Repositories" section: public code repo, private
  data repo (sibling folder), private frozen archive; where real cases are opened and
  saved; run `check.sh` before merging verdict-affecting changes; install the hook.
- `docs/training/` — paths to real projects point to the data folder; examples use the
  anonymised `P-9xxx` projects.
- `docs/changes/NEXT_STEPS.md` — owner steps below, until done.

## Owner steps (after this sprint; prepared, not run, by the orchestrator)
1. On GitHub: rename `CentrifugalPump` → `CentrifugalPump-archive`, keep it **private**.
2. `tools/make_public_snapshot.sh ../CentrifugalPump-public`, review, create the public
   repo `CentrifugalPump`, push.
3. Create private `CentrifugalPump-data`, push `../CentrifugalPump-data`.
4. Public repo settings: secret `LEAK_WORDLIST` (contents of `wordlist.txt`); Pages
   source "GitHub Actions"; run the Pages workflow.
5. Locally: point this folder's `origin` at the archive, or re-clone the public repo
   into `~/GitHub/CentrifugalPump`.

## Reuse
- `tools/leak_scan.py`, `tools/install_hooks.sh`, `pumpflow.export_cli`.

## Tests
- `tests/test_public_snapshot.py`: run the script on a tmp clone with a toy word list:
  a clean tree gives a one-commit repo; a planted word aborts it.
- `../CentrifugalPump-data/check.sh` passes against the current code.

## Acceptance
```bash
pytest -q
bash tools/make_public_snapshot.sh "$TMPDIR/public-snap" && git -C "$TMPDIR/public-snap" log --oneline
(cd ../CentrifugalPump-data && ./check.sh)
```

## Definition of done
Snapshot script produces a clean one-commit repo; data folder has README, map, word
list, expected results and `check.sh`; docs describe the workflow; project marked
`Status: ready to archive`.

## Assumes
Sprint 4: Pages workflow and sub-path build exist; sprint 2's data folder exists.
