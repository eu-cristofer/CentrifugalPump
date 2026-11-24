# Sprint 3 — Leak guard: pre-push hook and CI job

## Goal
No push and no CI build can carry a confidential word into the public repo.

## Files
- `tools/hooks/pre-push` — runs `tools/leak_scan.py --git-range` on every ref being
  pushed (new branches: against `origin/main`, or all commits if no remote main).  Word
  list from `$PUMP_WORDLIST`, default `../CentrifugalPump-data/wordlist.txt`.  If the list
  is missing, it **blocks** the push with a message (set `PUMP_WORDLIST` or
  `PUMP_LEAK_SKIP=1` to override knowingly).
- `tools/install_hooks.sh` — sets `git config core.hooksPath tools/hooks`.
- `.github/workflows/ci.yml` — job `leak-scan`: writes the secret `LEAK_WORDLIST` to a
  temp file and scans the tracked files and the pushed range; when the secret is empty
  (fork PRs) it prints a notice and succeeds.  Blocking otherwise.
- `docs/contributing` section (or `README.md` "Development"): run `tools/install_hooks.sh`
  once after cloning.
- `CLAUDE.md` — the confidential-material rule points to the data folder and the hook.

## Reuse
- `tools/leak_scan.py` (sprint 1).

## Tests
- `tests/test_leak_hook.py`: tmp repo + tmp word list; a commit adding a listed word is
  blocked by the hook script; a clean commit passes; missing word list blocks.

## Acceptance
```bash
pytest -q tests/test_leak_hook.py && pytest -q
bash tools/install_hooks.sh && git config core.hooksPath
```

## Definition of done
Hook installed in this clone; CI job present and green locally simulated
(`LEAK_WORDLIST` from the data folder); docs tell contributors to install it.

## Assumes
Sprint 2: tree is clean against the word list, which exists at
`../CentrifugalPump-data/wordlist.txt`.
