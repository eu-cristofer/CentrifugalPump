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
- [ ] [Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2](sprint-2.md)
- [ ] [Sprint 3 — Unit choice on every GUI numeric field](sprint-3.md)
- [ ] [Sprint 4 — Complete head (pressure + velocity + elevation)](sprint-4.md)
- [ ] [Sprint 5 — Edition-aware acceptance engine](sprint-5.md)
- [ ] [Sprint 6 — UC-11 Mechanical run acceptance](sprint-6.md)
- [ ] [Sprint 7 — UC-08 Compare pumps (twin A vs B)](sprint-7.md)
- [ ] [Sprint 8 — UC-05 NPSH margin](sprint-8.md)
- [ ] [Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766)](sprint-9.md)
- [ ] [Sprint 10 — UC-07 Impeller trim](sprint-10.md)
- [ ] [Sprint 11 — UC-03 System curve + UC-04 Operating point](sprint-11.md)
- [ ] [Sprint 12 — UC-01 Pump selection](sprint-12.md)
- [ ] [Sprint 13 — UC-10 Educational mode + worked notebooks](sprint-13.md)
- [ ] [Sprint 14 — Masterpiece polish: report, CI, docs](sprint-14.md)

## Changelog

- Registered project 001_masterpiece (14 sprints) on `feat/masterpiece`.
- S1: `pump.constants` (`G` = 9.80665 m/s², `P_ATM`) replaces every literal 9.81. Derived heads rise by +0.034 %: B-34004A predicted H at 9.80 m³/h is 339.43 → **339.54 m**, while P (24.61 kW) and η (36.80 %) are unchanged and the verdict is still APPROVED.
- S1: kinematic viscosity (cSt) is a standard unit, so the binding no longer needs warning suppression.
- S1: `pump.Pressure` adds gauge/absolute semantics: differences carry no reference, and mixing references is an error.
- S1: `pump.quantity_io` provides `{"value", "unit"}` JSON round-trips.
- S1: `Water` gains `dynamic_viscosity`, `kinematic_viscosity` and `vapour_pressure` (IAPWS-IF97 Eq. 30). The water helpers in `pumpflow` now delegate to the library.
