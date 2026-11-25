# Dev Journey: your map when it feels like too much

> *A use case is a thin flow over the domain, proven by one test.*

Read this first when you join the project, or whenever the repo feels overwhelming.
It turns *"there's too much to do"* into *"here is the next one thing."*

## Where we are (2026-11)

- **001_masterpiece is done.** It covers:
  - the edition-aware API 610 engine (8th/10th/11th/12th, plus client overlays);
  - the 18-node desktop workbench;
  - Word, LaTeX/PDF and HTML reports in English and Portuguese;
  - the Annex M test data summary.
- **002_web is done.** The same engine runs in the browser (Pyodide), works offline, and
  gives the same verdicts as the desktop.
- **003_public-split is done.** The code is public, customer data lives in a private
  repo, and the documentation and the web app publish to GitHub Pages on every merge.

Open items live in [changes/NEXT_STEPS.md](changes/NEXT_STEPS.md). Larger work is
planned as a numbered project under `docs/changes/`.

## The three repositories

| Repo | Visibility | Holds |
|---|---|---|
| `CentrifugalPump` (this one) | public | all code: `pump/`, `pumpflow/`, `web/`, docs, anonymised examples |
| `CentrifugalPump-data` | private | real projects, the company report form, the anonymisation map, the leak-guard word list, the real-case verdict check |
| `CentrifugalPump-archive` | private, frozen | the history before the split; never changes again |

There is **one codebase**. Desktop, library, web and docs changes all land here, so
nothing is ported between repos. The data repo never contains code.

## Setup (once per machine)

```bash
git clone https://github.com/eu-cristofer/CentrifugalPump.git
git clone <private url> CentrifugalPump-data       # beside it, if you have access
cd CentrifugalPump
pip install -e ".[dev,gui,docs]"                    # or: mamba env create -f environment.yml
sh tools/install_hooks.sh                          # leak guard on every push
npm --prefix web ci && npm --prefix web run vendor # only if you touch the web app
```

Without the data repo the pre-push hook has no word list and blocks the push. Ask for
access, or point `PUMP_WORDLIST` at the list you were given.

## The change loop

Every change, however small, follows the same path:

1. **Branch** from `main` (`feat/…`, `fix/…`, `docs/…`).
2. **Change** the code. Physics and verdicts go only in `pump/`; the workbench calls in
   only through `pumpflow/binding/`; TypeScript never computes.
3. **Run the local gates** that match what you touched:

   | You changed | Run |
   |---|---|
   | anything Python | `pytest` |
   | a file in CI's black list | `black <file>` |
   | `pump/` | `mypy pump --ignore-missing-imports` |
   | docs | `python -m sphinx -W -b html docs docs/_build/html` |
   | Python used by the web | `npm --prefix web run vendor && npm --prefix web run parity` |
   | `web/` | `npm --prefix web run check` |
   | anything that can move a verdict | `../CentrifugalPump-data/check.sh` (real cases) |

4. **Push and open a PR.** The leak guard scans your commits first. CI runs pytest on
   3.12 and 3.13, black, mypy, Sphinx `-W`, the web check/parity/build, and the leak
   scan. All of them block except the LaTeX job.
5. **Merge.** Pages redeploys the documentation (site root) and the web app (`/app/`)
   from `main`, so the public site always matches the desktop code.

## Files that guard the behaviour

Change these only on purpose, and say why in the commit:

- `examples/user/P-9001A_MRT_reference.pumpflow` and `tests/fixtures/v1/expected.json`:
  the regression fixture and its pinned node statuses.
- `examples/sample_project.pumpflow`: regenerate it from
  `pumpflow.sample_data.sample_project_doc()`; never edit the JSON by hand.
- `pump/standards/*.toml`: the acceptance criteria. Never invent a value: ship
  `verified = false` with an honest `source`.
- `pump/design/tokens.json`: every colour and size; no `#rrggbb` in code.
- Both `.po` files: every new report string goes into English **and** Portuguese.

## Real cases and confidentiality

- Real projects are opened from the data repo (desktop, or the web app's Open button)
  and saved back there. They never come into this repo.
- To publish a new example, anonymise a copy with `tools/anonymise.py` and the private
  map, then add the copy here in a PR.
- Never write a real tag, vendor, customer or document number in a file, a commit
  message or a PR. Examples use `P-9xxx` and "Vendor A".
- Notebooks are committed without image outputs, because a chart title drawn in pixels
  cannot be scanned (`tests/test_notebook_images.py`).
- Standard texts are licensed. Quote clause numbers and short phrases only.

## The two rules

**1. Only ever look at the next sprint.** Open the first unchecked item of the active
project in `docs/changes/`, finish it, come back. Don't hold the whole backlog in your
head.

**2. Structure by domain, steer by use cases.**

| Layer | Where | Organised by |
|---|---|---|
| Capabilities (stable nouns) | `pump/` | the domain |
| Flows (capabilities wired into user actions) | `pumpflow/`, `web/` | user-facing pipelines |
| Priority and acceptance | `docs/product/use-cases.md` | the use cases |

If a use case needs a new noun (NPSH, trim, system curve), it goes into `pump/` as a
capability. If it only arranges existing nouns, it is a flow plus an acceptance test.

## Take one use case to production

1. **Frame it** in [use-cases.md](product/use-cases.md): actor, trigger, input, output,
   and one acceptance sentence.
2. **Find the gap.** Does `pump/` already have the capability?
3. **Add the capability first** if it's missing. It takes and returns `Q_` quantities,
   and has doctests.
4. **Write the failing acceptance test**, then compose the flow (a binding function and a
   node) until it passes.
5. **Check it against the reference**: numbers must agree with the standard or worked
   example, not just run.
6. **Document**: docstrings, the use case marked ✅, a CHANGELOG bullet, and the
   training material (`docs/training/`, `docs/concepts/`, the notebooks generated by
   `use_cases/build_notebooks.py`).

## When you're stuck inside a sprint

1. **Shrink the unit.** A sprint too big to start is two sprints.
2. **Write the assertion first**, so the job becomes making one line go green.
3. **Narrow a sprawling diff.** If it sprawls, you took on too much: stash it, narrow it,
   resume.
4. **Lean on the rules in `CLAUDE.md` and the ADRs.** They are decisions you don't
   have to make again.

## Where to read next

- [ARCHITECTURE.md](ARCHITECTURE.md): the system map.
- [UI_SPEC.md](UI_SPEC.md): the workbench spec (cited as `UI_SPEC §N`).
- [web.md](web.md): running, building and serving the web app.
- [RUN_AND_TEST.md](RUN_AND_TEST.md) and [BUILD.md](BUILD.md): commands in depth.
- [adr/README.md](adr/README.md): the architecture decisions (0012, the single verdict
  engine; 0013, the web version).
