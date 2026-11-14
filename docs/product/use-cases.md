# Use-case registry

> Single source of truth for *what the project must do*, with each use case scored
> against the **current** library. Supersedes the React-era spec; all GUI references
> are mapped onto the PySide6 [`pumpflow/`](../../pumpflow/) package (see
> [audience.md](audience.md#repo-vs-spec-discrepancy)).

**Status key:** ✅ supported · 🟡 partial · ❌ gap.
**Priority** is a recommendation pending project-owner sign-off.

## Priority summary

| Priority | Use cases | Rationale |
|---|---|---|
| **Must ship (MVP)** | UC-00, UC-02, UC-06 (library), UC-09 | What the codebase already does or nearly does — the primary value to the FAT engineer. UC-00 is the units/fluids foundation the other three stand on. |
| **Defer to v1.1** | UC-01, UC-03, UC-04, UC-05, UC-07, UC-08 | All depend on new library work (selection catalogue, system curve, NPSH, impeller-trim branch, comparison plotting). |
| **Out of scope** | UC-10 (educational mode) | Low repo evidence of demand; thin layer over concept docs in v1.2+. |

## MVP use cases

### UC-00 — Work in the engineer's own measurement units ✅
- **Foundation.** Use case zero — the units/fluids layer every other use case
  stands on, scored first because nothing downstream is unit-consistent without it.
- **Actor:** FAT engineer / test technician (primary). **Trigger:** transcribing
  gauge, datasheet, or instrument readings that arrive in mixed units
  (bar, kgf/cm², psi, m³/h, gpm, rpm, °C) and defining the test fluid.
- **Input:** raw magnitudes tagged with whatever unit the instrument reports,
  plus a fluid (name + density, or `Water` at a temperature).
- **Output:** quantities normalized to the project's standard units so every
  downstream computation (head, power, η, affinity) is unit-consistent, and
  results convert back to the engineer's display units without loss.
- **Supported by:** the **units spine** — `quantity_factory` / `STANDARD_UNITS` /
  `extract_context` ([`pump/utilities/unit_conversion.py`](../../pump/utilities/unit_conversion.py)),
  `Fluid` and `Water` ([`pump/utilities/fluid.py`](../../pump/utilities/fluid.py));
  surfaced in the workbench via the units registry + `UnitField` + project preset
  ([`pumpflow/`](../../pumpflow/)).
- **Acceptance:** a value entered in any dimensionally-compatible unit normalizes
  to its standard unit and round-trips back without loss; the `unit_conversion`
  doctests and `tests/test_utilities.py` pass.
- **Pinned by:** `tests/test_utilities.py` + the worked utilities-demo notebook
  (the consolidated `use_cases/UC-00_…` example).

### UC-02 — Verify pump performance (FAT) ✅
- **Actor:** FAT engineer (primary). **Trigger:** performance test / report drafting.
- **Input:** rated nameplate + measured test points.
- **Output:** fitted H-Q / P-Q / η-Q curves, deviation table vs nameplate,
  pass/warn/fail verdict per metric and overall.
- **Supported by:** `PerformanceCurve`, `PerformanceChecker`
  ([`pump/performance_curve.py`](../../pump/performance_curve.py)); GUI Results path in
  [`pumpflow/nodes/compliance.py`](../../pumpflow/nodes/compliance.py).
- **Acceptance:** predicted H, P, η at rated Q match
  `PerformanceChecker.report_summary` within floating-point tolerance.
- **Pinned by:** `tests/test_compliance.py` (Sprint S2).

### UC-06 — Evaluate speed change (VFD) ✅
- **Actor:** application engineer. **Trigger:** VFD / speed-trim study.
- **Input:** a measured `PerformanceCurve` + target speed N₂.
- **Output:** new curve at N₂ with H, P, η transformed by the affinity laws.
- **Supported by:** `PerformanceCurve.to_speed`
  ([`pump/performance_curve.py:435`](../../pump/performance_curve.py#L435)).
- **Acceptance:** round-trip `curve.to_speed(N).to_speed(N0)` differs from the
  original by `< 1e-6` at corresponding Q.
- **Pinned by:** `tests/test_affinity.py` (Sprint S2).

### UC-09 — Generate report 🟡
- **Actor:** FAT engineer (primary). **Trigger:** test complete, deliverable due.
- **Input:** a `PerformanceChecker.report_summary`-style structure.
- **Output:** `.docx` **today**; `.pdf` / `.html` / `.json` **planned**.
- **Status:** `.docx` works (`pump.utilities.report.ReportGenerator`); other formats
  are not yet wired to a backend.
- **Acceptance:** round-tripping an existing example reproduces the same data
  structure and tables.
- **v1.1 follow-on:** implement PDF / HTML / JSON exporters.

### UC-11 — Mechanical running test acceptance ✅
- **Actor:** FAT witness / inspector (primary). **Trigger:** the mechanical run
  (typically 4 h at rated flow) is being logged every 15 min.
- **Input:** a time-stamped log of channels in any unit (flow, ΔP, power,
  filtered/unfiltered vibration, bearing/oil temperatures, lube-oil and seal
  pressures), each tagged with a role.
- **Output:** per-channel min/max/last vs limit, temperature-stabilisation
  check, duration check, overall verdict (PASSED / FAILED / PASSED (not fully
  assessed)), trend plot, and a "Mechanical running test" report section.
- **Supported by:** `pump.mechanical_run` (`MechanicalRunLog`,
  `MechanicalRunChecker`, `plot_mechanical_run`), limits in
  `pump/standards/api610.toml` (`mechanical_run`, unverified seeds), the
  `mechanical_run` workbench node.
- **Pinned by:** `tests/test_mechanical_run.py` (incl. the B-34004A 4 h record),
  `tests/test_mechanical_run_gui.py`.
- **Open:** vibration / stabilisation limits must be confirmed by the owner
  (shipped `verified = false`).
  - Against the placeholder 3.0 mm/s seed limit, B-34004A's unfiltered vibration of 0.16 in/s (4.06 mm/s) reads as **FAILED**.
  - That limit came from the reference notebook and isn't confirmed for this OH6 pump, so the API 610 vibration limits the owner supplies will decide the real verdict.

## Deferred to v1.1 (library gaps — recorded, not built in this plan)

| UC | Title | Why deferred |
|----|-------|--------------|
| UC-01 | Select a pump for given conditions | No pump catalogue in the library. |
| UC-03 | Analyse system curve | No system-curve module. |
| UC-04 | Find operating point | Blocked by UC-03. |
| UC-05 | Check NPSH margin | No NPSH module. |
| UC-07 | Evaluate impeller trim | Diameter affinity branch not implemented. |

## Out of scope

### UC-10 — Learn pump fundamentals 🟡
Interactive educational diagrams. Low repo evidence of demand; revisit in v1.2+.
