# 003_public-split — public code repo, private data repo, GitHub Pages

Splits the project in two: a **public** repo with all the code (library, desktop
workbench, web app, docs) and anonymised examples, and a **private** data repo with the
customer originals (PDFs, real `.pumpflow` projects, real reports).  Company names are
replaced and tags are mapped to `P-9xxx`; measured numbers are left untouched, so every
verdict stays the same.  A leak guard (pre-push hook + CI) blocks confidential words, and
GitHub Pages publishes the documentation and the web app from `main`.  Today's repo
becomes a frozen private archive.

See [MOTIVATION.md](MOTIVATION.md) for the why, the decisions and the risks.

Status: ready to archive · Branch: feat/public-split · Baseline commit: 128bf22

# 003_public-split — Loop Protocol

Each run MUST:
1. Read this README top to bottom. Pick the FIRST sprint whose checkbox is `[ ]`.
   Never skip ahead; never start a sprint whose predecessor is unchecked.
2. Open its sprint-N.md and verify the "Assumes" line against the code. If an
   assumption fails, fix forward only if trivial; otherwise write
   `BLOCKED: <reason>` under the tracker line and STOP (do not tick).
3. Implement exactly the sprint's scope (via `/sprint-loop next 003_public-split` or
   `/sprint-loop run 003_public-split`: the drafter drafts, the orchestrator
   reviews/applies). Resist scope creep.
4. Run the sprint's Acceptance commands — all must pass.
5. Update the changelog (one bullet per user-visible change).
6. Tick the checkbox `[x]` and append `— done YYYY-MM-DD`.
7. Commit in one commit: `003_public-split sprint N: <title>`.
8. When all sprints are checked, mark the project `Status: ready to archive` and
   archive it later with `/sprint-loop archive 003_public-split`.

## Standing rules (every sprint)

- **No real names in this project's own files.**  The map (real → public) and the
  word list live only in the data folder `../CentrifugalPump-data/` (outside this repo).
  Sprint files say "the map" and "the word list"; they never quote a real tag, vendor,
  customer or document number.
- **Numbers untouched.**  Anonymisation is string replacement on names and tags only;
  measured values, test numbers and every verdict stay identical.
- **One engine** (ADR 0012), **same answers** desktop = headless = browser (`parity`).
- **Gates.** `pytest` green; `npm --prefix web run check` and `parity` green; black on
  new Python files (add them to the CI black list).
- **Nothing is pushed to GitHub, and no repo is created, renamed or made public, by a
  sprint.**  Those are the owner's steps after sprint 5 (see sprint-5.md, "Owner steps").

## Tracker

- [x] [Sprint 1 — Anonymiser and leak scanner](sprint-1.md) — done 2026-11-23
- [x] [Sprint 2 — Apply: originals to the data folder, anonymised copies in the repo](sprint-2.md) — done 2026-11-23 (also: neutral Word templates; real docx reports removed, not regenerated)
- [x] [Sprint 3 — Leak guard: pre-push hook and CI job](sprint-3.md) — done 2026-11-23
- [x] [Sprint 4 — GitHub Pages: documentation and web app](sprint-4.md) — done 2026-11-23
- [x] [Sprint 5 — Cutover kit, data repo skeleton and docs](sprint-5.md) — done 2026-11-23
