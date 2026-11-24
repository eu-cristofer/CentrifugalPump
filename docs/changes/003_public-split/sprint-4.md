# Sprint 4 — GitHub Pages: documentation and web app

## Goal
One Pages site from `main`:

```
https://<owner>.github.io/CentrifugalPump/       Sphinx documentation
https://<owner>.github.io/CentrifugalPump/app/   the web app (installable, offline)
```

## Files
- `web/vite.config.ts` — `base: process.env.PUMPFLOW_BASE ?? "/"` (default keeps
  `dev`, `serve`, `dev:lan` and `parity` working at the root).
- `web/src/engine/worker.ts` — `PY_BASE = import.meta.env.BASE_URL + "py/"` (today a
  hard-coded `"/py/"`).
- `web/scripts/sw.mjs`, `web/scripts/sw-lib.mjs`, `web/src/sw/register.ts` — service
  worker registered at `BASE_URL + "sw.js"` with scope `BASE_URL`; precache list built
  relative to the base.  Check `web/index.html` asset paths resolve under the base.
- `web/scripts/tokens.mjs` — manifest `start_url`/`scope` are already `"."`; keep.
- `.github/workflows/pages.yml` — on push to `main` and `workflow_dispatch` (never on
  PRs); permissions `pages: write`, `id-token: write`:
  1. Python 3.12, `pip install -e ".[docs]"`, `sphinx-build -W -b html docs _site`.
  2. Node 22, `npm --prefix web ci`, `vendor`, `check`, `parity`, then
     `PUMPFLOW_BASE=/${{ github.event.repository.name }}/app/ npm --prefix web run build`;
     copy `web/dist` to `_site/app`.
  3. Leak scan over `_site` with the `LEAK_WORDLIST` secret (skip with notice if empty).
  4. `actions/upload-pages-artifact` + `actions/deploy-pages`.
- `docs/index.rst` and `README.md` — "Open the web app" link (relative `app/` in the
  docs; full Pages URL in the README).
- `.readthedocs.yaml` — removed (docs live on Pages).
- `docs/web.md` — the public address, the sub-path build (`PUMPFLOW_BASE`), and that
  local serving is unchanged.
- `docs/changes/002_web/MOTIVATION.md` — "Open decisions: hosting" becomes a decision:
  GitHub Pages, 2026-11-23 (link to this project).
- `docs/changes/NEXT_STEPS.md` — hosting item closed.

## Reuse
- The existing CI `web` and `docs` job steps in `.github/workflows/ci.yml` (copy the
  setup; pin the same action versions).
- `web/src/sw/register.ts` options (`enabled`, `container`) for tests.

## Tests
- vitest: worker `PY_BASE` and service-worker URL/scope derive from `BASE_URL`
  (mock `import.meta.env.BASE_URL = "/X/app/"`).
- Local end-to-end: build docs + app with `PUMPFLOW_BASE=/CentrifugalPump/app/` into
  `$TMPDIR/site/CentrifugalPump/`, serve `$TMPDIR/site` with `python -m http.server`,
  open `/CentrifugalPump/` (docs) and `/CentrifugalPump/app/` (engine boots, an example
  opens, "Ready offline" on localhost).

## Acceptance
```bash
npm --prefix web run check && npm --prefix web run parity
PUMPFLOW_BASE=/CentrifugalPump/app/ npm --prefix web run build
npm --prefix web run build          # root build still works
sphinx-build -W -b html docs "$TMPDIR/site/CentrifugalPump"
pytest -q
```
Plus the local end-to-end check above.

## Definition of done
Workflow file ready; sub-path and root builds both work; docs link to the app; hosting
decision recorded.

## Assumes
Sprint 3: leak scanner and `LEAK_WORDLIST` convention exist; 002_web's `web/` app with
`scripts/sw.mjs` and `src/sw/register.ts`.
