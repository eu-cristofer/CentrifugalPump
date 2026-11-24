# Sprint 9 — CI parity job, docs and training

## Goal
Keep the web version honest after the project ends: CI proves browser = desktop on
every push, and the docs and training explain the web version.

## Files
- `.github/workflows/ci.yml` — new job `web`: setup Node (pinned), Python 3.12,
  `npm ci`, `vendor`, `check`, `parity`, `build`; upload `web/dist` as an artifact.
  Add the new Python files to the black list.
- `docs/UI_SPEC.md` — new section "Web version": scope (witness kinds), what differs
  from the desktop (side-panel forms, no LaTeX/PDF, print to PDF), offline rule.
- `docs/ARCHITECTURE.md` — engine / webapi / worker diagram.
- `docs/adr/0013-web-version-pyodide.md` — decision record (one engine in Pyodide,
  offline bundle, React Flow; alternatives: server, iOS native, TS rewrite).
- `docs/training/` — TR note "Witnessing with the browser version" (open, enter
  data, export, offline check).
- `README.md`, `CLAUDE.md` — commands for `web/` (`npm --prefix web run dev/check/parity`)
  and the engine/webapi layer.
- `docs/changes/NEXT_STEPS.md` — remaining web items (other node forms, LaTeX/PDF,
  dark theme for web).

## Reuse
- Existing CI layout in `.github/workflows/ci.yml`; ADR template from
  `docs/adr/0012-*`.

## Tests
- CI `web` job green on the branch.
- `pytest -q` green; Sphinx `-W` not made worse.

## Acceptance
```bash
pytest -q
npm --prefix web run check && npm --prefix web run parity && npm --prefix web run build
```

## Definition of done
CI fails if the browser ever disagrees with the desktop on the fixtures; docs, ADR and
training describe the web version; project marked `Status: ready to archive`.

## Assumes
Sprint 8: complete web app with reports and offline install.
