# Why 001_masterpiece exists

## The problem

The P-9001 witness preparation (Nov 2026) loaded a real Vendor A certified test (P-9001A, Model M1, integrally geared) into `pumpflow` and produced docx/tex/pdf reports. It worked, but it exposed the weaknesses below.

1. **Units are only half Pint.** Only Rated Point, Point and Fluid use `UnitField` and `units.to_standard`. Everything else is a raw float in an implied unit:
   - the whole Test Points table (Q m³/h; pressure bar/kgf/cm² only; °C; rpm; kW);
   - rated speed, efficiency, shut-off head and NPSHa;
   - the correction target speed;
   - the plot y-limits.

   The vendor sheet was in gpm, psi, °F and hp, and every value had to be converted **by hand** before entry. That is an error source a FAT tool must eliminate.
2. **Pressure bypasses Pint.** `pumpflow/binding.py` uses a hand table `_PA_PER` (bar and kgf/cm² only; an unknown unit silently becomes bar). There is no gauge/absolute concept, which NPSH needs.
3. **Signals carry floats.** Payloads such as `TestRow.q_m3h` and `RatedPoint.speed_rpm` encode the unit in the name, and `binding.py` re-wraps them with literal unit strings.
4. **The physical head is incomplete.** `pump.point.TestPoint` can add velocity and elevation head, but `binding.correct_curve` pins `_head` from ΔP only. g is 9.81 in places instead of 9.80665.
5. **Acceptance is not standard-aware.**
   - Head tolerance is a hard-coded ±3 %.
   - The shut-off tier is keyed differently in the library (rated head) and the GUI (shut-off head).
   - Review findings F-01, F-02, F-05 and F-07 are open.
   - The report cites "API 610 12th issue" even for an 8th-edition pump.
6. **Use cases missing.** Pump selection, system curve, operating point, NPSH margin, impeller trim, comparison, educational mode and viscosity correction (a disabled checkbox) are all missing. The **mechanical running test**, half of the FAT being witnessed, does not exist at all.

## Levers / approach

- **Units first (S1–S4).**
  - Pint quantities flow from input to signal to library to report.
  - Files store `{"value", "unit"}` pairs (schema v2) with a lossless migrator from v1.
  - Every numeric field gets a unit choice, and the Test Points table gets per-column units.
- **FAT acceptance next (S5–S7).**
  - Data-driven tolerance tables per standard/edition with a client overlay (N-553).
  - Mechanical-run acceptance (UC-11).
  - Twin comparison A vs B.

  These directly serve the P-9001B witness test.
- **Engineering use cases (S8–S12).** NPSH, HI 9.6.7 viscosity, impeller trim, system curve + operating point, selection. Each is new library physics behind a node.
- **Learning + polish (S13–S14).** Worked notebook per UC, concept docs, a report cover page and all sections, HTML export, and CI (pytest, black, mypy, LaTeX).

## Key decisions (2026-11-14)

| Decision | Choice | Why |
|---|---|---|
| Scope | All registered UCs + new UC-11 mechanical run | The owner wants the full product. The mechanical run is what is witnessed. |
| Units model | Value+unit pairs, schema v2, migrator, Quantities in signals | Pint becomes the single truth. Removes the implied-unit hazards found in the audit, including the preset-vs-missing-`*_unit` hazard. |
| Viscosity method | HI 9.6.7 / ISO TR 17766 | This is the current recognised method. The notebook factors are a placeholder. |
| Execution | sprint-loop, one sprint per run, owner reviews between runs | New physics needs owner sign-off between steps. |
| PDF | Compiled from LaTeX (already shipped in `2e1983a`) | Deterministic, and needs no Word. |

## Risks

1. **Standards values.** The repo owner must supply or confirm:
   - tolerance tables per API 610 edition;
   - vibration limits;
   - N-553 overrides;
   - the HI 9.6.7 worked example.

   **Mitigation:** values ship as `verified = false` with a `source` string, and tests pin only confirmed values.
2. **Schema v2 is a breaking file-format change.** **Mitigation:**
   - migration on every load;
   - bit-identical verdict and H/P/η tests over every shipped `.pumpflow`;
   - old files are not overwritten unless the user saves.
3. **The S2 signal refactor touches every node.** **Mitigation:** the full regression suite gates the sprint. If it overruns, split it into "binding/persistence" and "nodes" (note the split in the tracker).
4. **New physics (S8–S12) could be wrong in subtle ways.** **Mitigation:** each sprint pins a hand calculation or a published example, and its `Assumes` line requires owner sign-off on the method.
5. **Qt-dependent tests.** **Mitigation:** run them offscreen (`QT_QPA_PLATFORM=offscreen`), skipped cleanly without PySide6. Library tests stay Qt-free.
