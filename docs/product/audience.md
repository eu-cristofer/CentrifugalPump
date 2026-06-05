# Audience

> Single source of truth for *who this project is for*. Supersedes any
> persona notes from the earlier React-era spec (`PumpLabGUI/*.jsx`,
> `phase1/00_phase_spec.md`), which **do not exist in this repository** — see the
> [repo-vs-spec note](#repo-vs-spec-discrepancy) below. The real interface is the
> PySide6 [`pumpflow/`](../../pumpflow/) workbench.

## Primary — Performance test / FAT engineer

The person the library is built for. Runs Factory Acceptance Tests and drafts the
client deliverable.

- **Knows:** how to read a pump curve (head / flow / power / efficiency / NPSH) and
  the API 610 tolerance bands cold.
- **Evidence in-repo:**
  - `PerformanceChecker` tolerance defaults — ±3 % head, +4 % power, tiered shutoff
    per rated head — at
    [`pump/performance_curve.py:637-668`](../../pump/performance_curve.py#L637-L668).
    These numbers are only intelligible to someone fluent in API 610 §8.3.
  - FAT / API 610 §8.3.3.4.3 report text at
    [`pump/utilities/report.py:189-305`](../../pump/utilities/report.py#L189-L305).
  - The worked example notebooks ([`examples/B-432301D.ipynb`](../../examples/B-432301D.ipynb),
    [`examples/52-P-11AB.ipynb`](../../examples/52-P-11AB.ipynb)) walk a complete FAT
    workflow.
- **Tools today:** Jupyter notebooks + Microsoft Word (the `.docx` reports in
  [`examples/`](../../examples/)). The [`pumpflow/`](../../pumpflow/) workbench is
  intended to replace the notebook workflow with a guided UI.
- **Environment:** desktop / laptop (the `python-docx` `.docx` output is a
  desktop-office artefact; nothing in the codebase is mobile-first).
- **Language:** bilingual EN / PT — dual templates
  [`pump/templates/template_en.docx`](../../pump/templates/) and `template_pt.docx`,
  plus gettext `.po` locale files for both.

## Secondary — Application / selection engineer *(pending owner sign-off)*

Selects pumps, analyses system curves, finds operating points, checks NPSH margins,
evaluates impeller trim. **Every one of these is a library *gap* today** (see
[use-cases.md](use-cases.md)); repo evidence for this persona is thin, so it is a
v1.1 audience pending confirmation.

## Tertiary — Student / learner *(pending owner sign-off)*

Self-study / onboarding. Low repo evidence of demand; treated as out of MVP scope.

## Roles explicitly out of scope

Plant maintenance engineers, rotating-equipment consultants, and pump sales
engineers appeared in the earlier React-era spec template but have no supporting
evidence in this codebase. Out of scope unless the owner asserts otherwise.

## Repo-vs-spec discrepancy

The persona/use-case material this project was seeded from cites
`PumpLabGUI/app-shell.jsx`, `PumpLabGUI/screen-*.jsx`, `docs/concepts/0X-*.md`,
`docs/library-audit.md`, and `phase1/00_phase_spec.md`. **None of these exist in
this repository.** They describe a parallel/earlier React prototype. This repo's
interface is the PySide6 package [`pumpflow/`](../../pumpflow/); its engineering math
lives in [`pump/`](../../pump/). All persona evidence above is re-anchored to files
that actually exist here.
