# Sprint 8 — Reports in the browser + installable offline app

## Goal
Export the witness report from the browser and make the app installable and fully
offline after the first load.

## Files
- `web/src/forms/ReportExportForm.tsx` — cover fields (project, client, location,
  date, revision, equipment table, signatories), language en/pt, formats
  **docx**, **html**, **xlsx test summary**; "Export" downloads the files returned by
  `webapi.export_report`; "Print to PDF" opens the HTML report in a new tab and calls
  `print()`.  LaTeX/PDF shown as "desktop only" with a one-line explanation.
- `web/public/sw.js` + registration — service worker caching the app shell and every
  file in `web/public/py/manifest.json` (cache-first, versioned by the manifest hash);
  `manifest.webmanifest` + icons (generated from tokens, no external assets).
- `web/src/App.tsx` — first-run loading screen with progress (bytes of the
  manifest), "Ready offline" indicator, update prompt when a new version is cached.
- `docs/web.md` (new) — how to build, serve (`npx vite preview` or any static
  server; `python -m http.server -d web/dist`), install, and what stays on the machine.
- Resolve the hosting open decision in `MOTIVATION.md` (record the user's choice).

## Reuse
- `pumpflow.webapi.export_report`; `pumpflow/nodes/report_export.py` (settings and
  `overall_verdict_text`); `pumpflow/export_cli.py` report path as the reference
  output.

## Tests
- pytest: `export_report` docx for P-9001A has the same paragraphs/verdict sentences
  as `export_cli` docx (compare extracted text); html contains the override sentence
  when tolerances are overridden.
- Vitest: service worker precache list equals the manifest + shell files.
- Manual check recorded in the sprint commit: load once, go offline (DevTools), reload,
  open P-9001A, export docx.

## Acceptance
```bash
pytest -q
npm --prefix web run check && npm --prefix web run parity && npm --prefix web run build
```

## Definition of done
Report files exported in the browser match the desktop's docx/html content; the app
reloads and works with the network off.

## Assumes
Sprint 7: all witness forms; `export_report` (sprint 3).
