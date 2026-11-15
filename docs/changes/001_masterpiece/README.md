# 001_masterpiece — Pint end to end, every use case, FAT-grade acceptance

Takes `centrifugal-pump` from "MVP that verifies a performance test" to a complete
FAT workbench:
- every numeric input and signal is a Pint quantity, with value+unit persistence (schema v2);
- the head is complete (pressure + velocity + elevation);
- acceptance is edition-aware and data-driven;
- a mechanical-run use case is added (UC-11);
- all registered use cases are delivered (UC-01/03/04/05/07/08/10, plus HI 9.6.7 viscosity correction);
- reporting and CI are polished.

See [MOTIVATION.md](MOTIVATION.md) for the why and the decisions.

Status: active · Branch: `feat/masterpiece` · Baseline commit: `2e1983a`

# 001_masterpiece — Loop Protocol

Each run MUST:
1. Read this README top to bottom. Pick the FIRST sprint whose checkbox is `[ ]`.
   Never skip ahead; never start a sprint whose predecessor is unchecked.
2. Open its sprint-N.md and verify the "Assumes" line against the code. If an
   assumption fails, fix forward only if trivial; otherwise write
   `BLOCKED: <reason>` under the tracker line and STOP (do not tick).
3. Implement exactly the sprint's scope (via `/sprint-loop next 001_masterpiece` or
   `/sprint-loop run 001_masterpiece`: the drafter drafts, the orchestrator
   reviews/applies). Resist scope creep.
4. Run the sprint's Acceptance commands — all must pass.
5. Update the changelog (one bullet per user-visible change).
6. Tick the checkbox `[x]` and append `— done YYYY-MM-DD`.
7. Commit in one commit: `001_masterpiece sprint N: <title>`.
8. When all sprints are checked, mark the project `Status: ready to archive` and
   archive it later with `/sprint-loop archive 001_masterpiece`.

## Standing rules (every sprint)

- **Physics location.** Physics lives in `pump/`. `pumpflow/` only orchestrates, and `pumpflow/binding.py` is the only adapter into `pump`.
- **No mutation.** Transforms (`to_speed`, `to_fluid`, …) and signals return **new instances**.
- **Pint everywhere.** Library constructors take Pint `Q_` quantities. Never introduce a new raw float with an implied unit. Normalise through `quantity_factory` / `STANDARD_UNITS` (extend the table rather than calling `.to()` ad hoc).
- **Gates.** `pytest` (full suite: `tests/` + `pump/` doctests) must be green. Run `black` on new files and on files that were already black-clean.
- **Regression fixture.** `examples/user/B-34004A_MRT_reference.pumpflow` must still evaluate. `python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf` must exit 0.
  - Branch A must stay **APPROVED**, with predicted H ≈ 339.4 m, P ≈ 24.6 kW and η ≈ 36.8 % at 9.80 m³/h.
  - Only a sprint that *intentionally* changes physics may move those numbers, and it must state the new values in its changelog bullet.
- **Use-case registry.** Update `docs/product/use-cases.md` status for the UC the sprint delivers.
- **Housekeeping.** Run `graphify update .` after code changes.
- **Changelog.** Bullets go in the "Changelog" section at the bottom of this README.
- **Standards values.** Never invent standard values: API 610 tolerances, vibration limits, HI 9.6.7 example data, N-553 overrides. Ship existing or user-confirmed values with `verified = false|true` and a `source` string. If a sprint needs a value nobody has confirmed, mark it unverified and say so in the changelog.

## Tracker

- [x] [Sprint 1 — Library quantity spine](sprint-1.md) — done 2026-11-14
- [x] [Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2](sprint-2.md) — done 2026-11-14
  - Split per the spec's overrun clause:
    - [x] 2a — signals carry Quantities, binding unit-free — done 2026-11-14
    - [x] 2b — `.pumpflow` schema v2 (`{"value","unit"}`) + `persistence.migrate` — done 2026-11-14
- [x] [Sprint 3 — Unit choice on every GUI numeric field](sprint-3.md) — done 2026-11-14
- [x] [Sprint 4 — Complete head (pressure + velocity + elevation)](sprint-4.md) — done 2026-11-14
- [x] [Sprint 5 — Edition-aware acceptance engine](sprint-5.md) — done 2026-11-14
  BLOCKED-PARTIAL: tolerance values unverified. API 610 8/10/11/12 are seeded with the pre-S5 code values and N-553 is an empty overlay, all `verified = false`, until the owner confirms them from the standard text.
- [x] [Sprint 6 — UC-11 Mechanical run acceptance](sprint-6.md) — done 2026-11-14
  BLOCKED-PARTIAL: mechanical-run limits unverified. The 4 h duration seed and the notebook vibration seeds (2.0 / 3.0 mm/s) are `verified = false`, and stabilisation is unconfigured.
- [x] [Sprint 7 — UC-08 Compare pumps (twin A vs B)](sprint-7.md) — done 2026-11-14
- [x] [Sprint 8 — UC-05 NPSH margin](sprint-8.md) — done 2026-11-14
  BLOCKED-PARTIAL: NPSH margin rule not configured. No ratio or margin is seeded, so the check reports "not configured" until the owner enters the N-553/API rule.
- [x] [Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766)](sprint-9.md) — done 2026-11-15
  Unblocked 2026-11-15. There is no free official worked example, so the equations (HI 9.6.7-2010 Eq. 2–7, secondary source) are validated by independent checks; see sprint-9.md.
- [x] [Sprint 10 — UC-07 Impeller trim](sprint-10.md) — done 2026-11-15
- [x] [Sprint 11 — UC-03 System curve + UC-04 Operating point](sprint-11.md) — done 2026-11-15
- [x] [Sprint 12 — UC-01 Pump selection](sprint-12.md) — done 2026-11-15
- [ ] [Sprint 13 — UC-10 Educational mode + worked notebooks](sprint-13.md)
- [ ] [Sprint 14 — Masterpiece polish: report, CI, docs](sprint-14.md)

## Open items needing owner input

Researched 2026-11-15. The main secondary source is the Amarinth technical bulletin MP2606-100 rev A, "Testing procedures API 610 10th and 11th". Values are stored in `pump/standards/api610.toml`, still `verified = false` because the standard text itself was not consulted.

- **Performance tolerances.**
  - Head: 11th edition ±3 % in every band; 10th edition +5/−2 % (0–150 m), +3/−2 % (151–300 m), ±2 % (> 300 m).
  - Shut-off: ±10/8/5 %. Power: +4 %. Both are corroborated.
  - The **8th edition is inferred from the 10th**, because no public 8th-edition text was found. B-34004A (333.8 m) therefore gets **±2 %** on head. Its predicted +1.72 % passes, but tightly, which is worth confirming with the 8th-edition table at the witness test.
- **Mechanical run.**
  - 4 h at rated flow, with oil-temperature stabilisation: confirmed by the source.
  - Horizontal-pump vibration (preferred region, **mm/s RMS**): overall 3.0, discrete 2.0 (allowable region 3.9 / 2.6). These match the earlier seeds.
  - **Open:**
    - B-34004A's unfiltered reading of 0.16 in/s is 4.06 mm/s if it is RMS (FAILED), but 2.87 mm/s if Sundyne's "IN/SEC" is peak (inside 3.0). Ask Sundyne which it is.
    - API 610's allowance for pumps above 3600 rpm / 300 kW per stage (this pump runs at 10 300 rpm) was not found and is not applied.
- **HI 9.6.7 viscosity correction.** Resolved for sprint 9: the equations come from a secondary source and are independently validated (see sprint-9.md).
- **NPSH margin rule.** No public API 610 / N-553 margin value was found, so it is still "not configured". (API 610 itself gives the NPSHr test a 0 % positive tolerance: the tested NPSH3 must not exceed the quoted value.)

## Changelog

- Registered project 001_masterpiece (14 sprints) on `feat/masterpiece`.
- S1: `pump.constants` (`G` = 9.80665 m/s², `P_ATM`) replaces every literal 9.81. Derived heads rise by +0.034 %: B-34004A predicted H at 9.80 m³/h is 339.43 → **339.54 m**, while P (24.61 kW) and η (36.80 %) are unchanged and the verdict is still APPROVED.
- S1: kinematic viscosity (cSt) is a standard unit, so the binding no longer needs warning suppression.
- S1: `pump.Pressure` adds gauge/absolute semantics: differences carry no reference, and mixing references is an error.
- S1: `pump.quantity_io` provides `{"value", "unit"}` JSON round-trips.
- S1: `Water` gains `dynamic_viscosity`, `kinematic_viscosity` and `vapour_pressure` (IAPWS-IF97 Eq. 30). The water helpers in `pumpflow` now delegate to the library.
- S2a: every signal payload now carries Pint quantities, and test-row pressures are `pump.Pressure`:
  - affected: `RatedPoint`, `FluidSpec`, `TestRow`, `TestPointSet`, `PointSample`, `CorrectedCurve.target_speed`;
  - the binding has no unit literals for signal fields (`_PA_PER`, `pressure_to_pa`, `row_head_m`, `row_efficiency_pct` removed; replaced by `row_head`, `row_efficiency`, `head_from_pressures`);
  - all 9 shipped projects evaluate **bit-identically** (states, statuses, every compliance number), and the exchange JSON is unchanged.
- S2a: fixed the Compliance dialog crashing when no rated point is wired, which happens on a blank branch. A new test opens every node dialog.
- S2b: `.pumpflow` **schema v2**. Every quantity is stored as `{"value", "unit"}` (Pint strings), and the Test Points table stores per-column units plus a pressure reference.
- S2b: old v1 files migrate automatically on open. Missing `*_unit` keys now take the canonical unit, never the active preset, which fixes a latent gpm/m³/h mix-up, and the stale rated `"unit"` key is dropped.
- S2b: the shipped examples and the B-34004A reference were re-saved as v2 with bit-identical results. Your own `examples/user/*` v1 files are untouched and still evaluate identically.
- S2b: found that Pint's `Hz` is 1/s while rpm is rev/min with 2π rad per rev. Speed units must use `revolution/second`, never `Hz`; this is noted in sprint 3.
- S3: every dimensional input has a unit choice.
  - New dimensions: pressure (kgf/cm², bar, psi, kPa, MPa, mH₂O) with a **g/a** reference, speed (rpm, rev/s), length, NPSH, efficiency and vibration velocity, plus extended SI/US presets.
  - Rated N, η, shut-off and NPSHa, the correction target speed, Point pressures and plot y-limits now use unit fields.
- S3: **Test Points has a unit per column**.
  - Changing a column's unit converts the stored values, which fixes the old relabel-only pressure combo.
  - g↔a conversion is lossless (5 decimals).
  - Pasted data can carry a header row, e.g. `Q [gpm]`, `P_dis [psi g]`.
- S3: **B-34004A re-entered exactly as Sundyne printed it** (gpm, psi g, °F, hp, pump rpm), with no hand conversion. Results change only by the old rounding: H 339.546 m (+0.0006 %), P 24.603 kW, η 36.80 %, still APPROVED.
- S3: on disk, units are always written in one compact Pint spelling, and unset plot limits are stored as bare `null`.
- S3: all other shipped projects evaluate bit-identically to S2.
- S3: the remaining plain spin boxes are dimensionless (tolerance %, SG).
- S4: **complete head**: H = ΔP/(ρg) + (v_d² − v_s²)/(2g) + (z_d − z_s), computed through `pump.TestPoint.compute_head`.
  - Optional test-bench geometry (pipe IDs and gauge elevations, any length unit) lives in Test Points.
  - The velocity head needs both pipe IDs, and the elevation head needs both elevations.
  - A measured head override still wins.
  - The Head column tooltip shows each component, and the report lists the geometry.
- S4: without geometry the results are bit-identical; all shipped projects are unchanged. Unset optional geometry is omitted on disk, so re-saved files match migrated ones.
- S5: acceptance criteria are **data**: `pump/standards/api610.toml` (editions 8, 10, 11, 12) plus a client overlay `clients/n553.toml`, loaded through `pump.acceptance.AcceptanceCriteria`.
  - **No row is verified.** Every edition carries the pre-S5 code values (head ±3 %, shut-off 10/8/5 %, power +4 %, η −3 %), marked unverified, and N-553 changes nothing until it is configured.
  - ISO 9906 is deferred, because no confirmed values exist.
- S5: the Rated Point gains Standard/edition and Client overlay pickers, and the edition is parsed from the old free text. B-34004A resolves to **API 610 8th + N-553**.
- S5: one deviation formula, (predicted − rated)/rated, is shared by the GUI and the library (review F-05).
  - Shut-off bands are keyed by rated differential head everywhere.
  - The GUI limits now equal the library's 2-decimal limits.
- S5: fixes:
  - F-01: `acceptable_limits` no longer crashes without shut-off or power data.
  - F-02: `check_summary` checks only the rated point.
  - F-07: an extrapolated shut-off is flagged.
- S5: new checks:
  - the parallel-operation rule (shut-off ≥ 110 % of rated head, unverified) fails the verdict when `parallel` is set and the rule isn't met;
  - the ignored `acceptable_limits` argument now warns.
- S5: the report states the selected edition instead of a hard-coded "12th issue" and lists the unverified criteria, in en and pt.
- S5: every shipped project's verdicts and limits are unchanged.
- S6: **UC-11 mechanical running test**. `pump.mechanical_run` adds:
  - a time-stamped log of quantities with per-channel roles and units;
  - a checker covering limits per role, temperature stabilisation over a window, minimum duration, and a PASSED / FAILED / "PASSED (not fully assessed)" verdict;
  - a trend plot.
- S6: limit seeds and sources live in `api610.toml` (all unverified):
  - 4 h duration, from the B-34004A record;
  - filtered vibration 2.0 mm/s and unfiltered 3.0 mm/s, from the reference notebook;
  - no stabilisation seed.
- S6: new **Mechanical Run** node. It has column/unit/role definitions, a readings grid with paste and unit headers, criteria overrides and a verdict. It feeds Report Export, and the "Mechanical running test" report section exists in en and pt.
- S6: B-34004A's 4 h Sundyne run is loaded (17 readings), plus a blank B-34004B sheet; a blank sheet is invalid rather than reporting a verdict.
  - Against the **unverified** notebook seed, A's unfiltered vibration of 0.16 in/s (4.06 mm/s) exceeds 3.0 mm/s, so the run shows **FAILED**.
  - The owner must enter the real limits for this OH6 pump. The filtered vibration of 0.05 in/s passes.
- S6: all other projects are unchanged.
- S7: **UC-08 compare pumps**. `pump.compare` adds `compare_curves` (H, P and η per tag at chosen Q, with Δ% against the first, reference curve) and `plot_comparison` (overlay of H, P and η).
- S7: any report with two or more fitted pumps (e.g. twin A vs B) gains a "Comparison" section in en and pt. The Explorer readout shows Δ% against the first model.
- S7: no separate compare node; the Explorer and the report cover the use case. All projects are unchanged.
- Fix (owner request, after S7): verdicts computed against criteria not verified from the standard text are now marked **provisional**.
  - The node status, the Compliance banner and the report verdict in en and pt now read "APPROVED (unverified criteria)" and "FAILED (unverified limits)".
  - B-34004A's mechanical run therefore reads **FAILED (unverified limits)**: a placeholder limit is never presented as a real test failure.
  - Numbers and pass/fail are unchanged. `tests/fixtures/v1/expected.json` changed only by these status suffixes.
- S8: **UC-05 NPSH**. `pump.npsh` provides:
  - NPSHa from suction conditions (absolute pressure, IAPWS vapour pressure, velocity and elevation);
  - NPSH3 from a 3 % head-drop sweep;
  - a fitted NPSHr curve with an extrapolation flag;
  - ratio and margin, plus an NPSH plot.
- S8: the margin rule is **not seeded**, so the verdict is "not configured" until the owner enters one; a rule entered but unverified is labelled "(unverified criteria)".
- S8: new **NPSH** node with direct NPSHr points or an NPSHa calculator; the 3 % sweep is library-only. An NPSH section appears in the reports (en/pt).
- S8: B-34004A has Sundyne's NPSHr points. NPSHr is 1.08 m (3.54 ft) at rated vs NPSHa 2.40 m, a ratio of 2.22, plus a blank B sheet.
- S8: `DesignPoint(NPSH_available=…)` is accepted as a deprecated alias of `npsha`.
- S9: **viscosity correction (HI 9.6.7)**. `pump.viscosity` provides `b_parameter` and `correction_factors`; `PerformanceCurve` gains `bep()` and `to_viscous()`.
  - The equations are HI 9.6.7-2010 Eq. 2–7 from a secondary source, validated independently: the US/SI constants agree, the factors are continuous at B = 1, and the method reproduces the legacy chart. They were not checked against the standard text.
- S9: the Correction node's "apply viscosity" now works (speed → density → viscosity). It shows B and the factors, and the report adds a "Viscosity correction (HI 9.6.7)" line when B > 1.
- S9: when B ≤ 1 (e.g. B-34004A wash water at 0.52 cSt) or viscosity is off, the results are bit-identical.
- S10: **UC-07 impeller trim**. `PerformanceCurve.to_diameter` uses diameter affinity and warns beyond 5 % trim; `pump.trim.diameter_for_duty` intersects the affinity parabola with the head fit (numpy only).
  - The Rated Point gains impeller nominal/min/max diameters, and there is a new **Trim** node (target diameter, or solve for rated duty).
  - B-34004A carries the datasheet diameters (128 / 125 / 131 mm). It needs **D = 127.1 mm (−0.7 %)** to hit its rated point exactly.
- S11: **UC-03/UC-04**. `pump.system_curve` provides static + k·Qⁿ (from k or two points) and Darcy–Weisbach pipe friction (Swamee–Jain); `pump.operating_point` intersects it with the pump curve (poly or spline) and flags extrapolation.
- S11: new **System Curve** and **Operating Point** nodes.
- S11: ADR-0009 is accepted. `NaturalCubicSpline`, `r_squared` and `bisect_root` now live in `pump.fitting`, and `pumpflow.mathx` re-exports them. The spline is bit-identical (verified on 200 random datasets).
- S11: overlaying the system curve on the Plot/Explorer was deferred. All projects are unchanged.
- S12: **UC-01 pump selection**. `pump.catalogue` adds a `*.pumpcurve.json` format (value+unit) and ranks candidates for a duty: as-is, speed-adapted or trimmed by affinity.
  - Ranking uses the preferred operating region (70–120 % BEP from a secondary source, unverified), then η at duty, then distance from BEP.
  - Trims outside [d_min, d_max] are rejected with a reason.
- S12: new **Selection** node; `examples/catalogue/` holds 3 curves built from the curated projects. For B-34004's duty it picks B-34004A at 127.1 mm, consistent with S10.
- Fix (found by the S12 drafter): the S11 system-curve codec entry had been inserted into the wrong table, so its units were not saved. It now lives in `FIELDS`, with a regression test.
