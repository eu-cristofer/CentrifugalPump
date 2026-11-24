# PumpFlow in the browser

The web version of the PumpFlow workbench runs the same Python (`pump` and the
`pumpflow` node logic) inside the browser through [Pyodide](https://pyodide.org), so the
verdicts are the desktop's verdicts.  Nothing is computed in JavaScript, and nothing
leaves the machine.  It is built from the `web/` folder and described by the project
[002_web](changes/002_web/README.md).

## Scope

- **Witness flow:** Rated Point, Fluid, Test Points, Speed correction, Curve fit,
  Performance plot, Compliance, NPSH, MRT Log, MRT Check, Report Export and Note.  Other
  node kinds open and evaluate, but say "Edit this node in the desktop app."
- **Reports:** Word (`.docx`), HTML and the API 610 test data summary (`.xlsx`) are
  exported in the browser from the Report Export form.  **Print to PDF** opens the HTML
  report in a new tab and the browser's print dialog; choose "Save as PDF".  The LaTeX
  and PDF report is **desktop only** (it needs a LaTeX installation).
- **Projects** are the same `.pumpflow` files as the desktop's: you open and save them
  as files.

## Build

You need Node 20 or newer and Python 3.12 (the Python is only used at build time, to
build the project wheel):

```bash
npm --prefix web ci
npm --prefix web run vendor    # downloads Pyodide and the wheels into web/public/py (network, once)
npm --prefix web run build     # tokens, vite build, then the offline service worker
```

`web/dist/` is the complete app (about 30 MB, mostly the Python engine).  `vendor` is the
only step that uses the network; the build and the app never do.  Run
`npm --prefix web run check` (types, lint, unit tests) and `npm --prefix web run parity`
(the browser engine against the desktop engine) before publishing a build.

## Serve

Any static server works.  It must serve over `http://localhost` or HTTPS (browsers do not
run service workers from `file://`), and the app must be at the root of its address:

```bash
python -m http.server -d web/dist 8080     # then open the localhost address, port 8080
# or
npx --prefix web vite preview              # serves web/dist
```

### On the home or office network

```bash
npm --prefix web run serve     # web/dist on port 8080, all network interfaces
npm --prefix web run dev:lan   # the dev server, same idea
```

Both print the addresses to use, for example `Network: http://192.168.15.16:8080/`.  Open
that address on the other device (iPad, phone, laptop) on the same Wi-Fi.  macOS may ask
once to allow incoming connections for `node`: allow it.  Over plain `http://` to an IP
address the browser does not run the service worker, so the app works while the server is
running but does not install for offline use; only `localhost` or HTTPS gives "Ready
offline".  Stop the server (Ctrl+C) when you are done: anyone on that network can open it.

Any static host serving `web/dist` over HTTPS (or localhost) works; the choice of host is
open (see [MOTIVATION.md](changes/002_web/MOTIVATION.md)).  The host only delivers the
files: it never sees a project or a report.

## Published site (GitHub Pages)

Every merge to `main` runs `.github/workflows/pages.yml`.  It builds the Sphinx docs and
the web app (`PUMPFLOW_BASE=/<repo>/app/ npm --prefix web run build`), scans the result
with the leak guard and deploys both as one GitHub Pages site:

```
https://<owner>.github.io/CentrifugalPump/       documentation
https://<owner>.github.io/CentrifugalPump/app/   web app
```

Local builds are unchanged: without `PUMPFLOW_BASE` the app is built for the root of
the address, as `npm --prefix web run serve` expects.  To try the sub-path build:

```bash
PUMPFLOW_BASE=/CentrifugalPump/app/ npm --prefix web run build
mkdir -p site/CentrifugalPump/app && cp -R web/dist/. site/CentrifugalPump/app/
python -m http.server -d site 8080     # open localhost:8080/CentrifugalPump/app/
```

Owner setup, once: repository Settings → Pages → Source "GitHub Actions", and the
`LEAK_WORDLIST` repository secret (without it the scan is skipped with a notice).

## Install and work offline

1. Open the app once while online.  The top bar shows "Saving for offline…" while the
   browser stores the app and the Python engine (about 30 MB), then "Ready offline".
2. After that the app starts and works with the network off.  Reloading, opening a
   project and exporting reports all work offline.
3. Optional: use the browser's "Install app" (address bar or menu) to open PumpFlow in
   its own window.

## What stays on the machine

Everything.  The Python engine runs in the browser; the project you open is read from
your file and held in memory; reports are produced in the browser and saved through the
download.  After the first load the app makes no network request.  The browser keeps
only the cached application files (a Cache Storage entry named `pumpflow-…`); projects
and reports are never stored by the app, so save your project with Save before you close
the tab.

## Updating

Publish a new `web/dist`.  The next time the app is opened online, the browser caches the
new version in the background and the top bar shows "Update available" with a Reload
button.  Reload applies it; the old version keeps working until then.

## Troubleshooting

- **Stuck on "Saving for offline…" or the engine does not start:** check that the page is
  served from `http://localhost` or HTTPS, from the root of the address.
- **A browser that blocks service workers (private window, strict policy):** the app
  still runs online, but there is no "Ready offline".
- **Print to PDF opens nothing:** allow pop-ups for the page; the report opens in a new tab.
- **Start over:** clear the site data for the address (browser settings, Site data, or
  DevTools, Application, Storage, Clear site data) and reload.
