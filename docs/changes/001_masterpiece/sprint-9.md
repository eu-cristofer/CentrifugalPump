# Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766)

## Goal
- A water-test curve can be converted to viscous performance with the HI 9.6.7 method, and the reverse direction too, for vendor curves stated on viscous liquid.
- A validity range applies, with a warning outside it.
- The Correction node's `apply_viscosity` checkbox, disabled today, becomes functional.

## Files
- `pump/viscosity.py` (new):
  - `b_parameter(nu, q_bep_w, h_bep_w, n)`;
  - `correction_factors(b, q_ratio) -> (C_Q, C_H, C_eta)`.
  - Method as commonly published for HI 9.6.7 / ISO TR 17766 in US units. **Verify every expression and coefficient against the standard text before merging**, and cite clause numbers in docstrings:
    - B = 26.6 · ν^0.50 · H_BEP-W^0.0625 / (Q_BEP-W^0.375 · N^0.25), with ν in cSt, H in ft, Q in gpm, N in rpm;
    - C_Q = 2.71^(−0.165 · (log10 B)^3.15);
    - C_H = 1 − (1 − C_Q) · (Q_W / Q_BEP-W)^0.75;
    - C_η = B^(−0.0547 · B^0.69);
    - corrections apply for 1 < B < 40; for B ≤ 1 there is no correction; for B ≥ 40 raise or warn ("outside method validity").
  - Inputs are Pint quantities, converted internally to the method's US units via `.to()`; outputs are dimensionless.
- `pump/performance_curve.py`:
  - `PerformanceCurve.bep()` returns (Q, H, η) at max η from the fitted curve;
  - `to_viscous(nu) -> PerformanceCurve` returns a **new instance** with Q·C_Q, H·C_H, η·C_η, and power recomputed from ρ_viscous;
  - it requires the target `Fluid` to carry density and kinematic viscosity.
- `pumpflow/binding.py` `correct_curve`:
  - order is speed → density → viscosity;
  - viscosity is applied when `apply_viscosity` is set and the target viscosity exceeds water's at test temperature;
  - surface the B value and the factors in `CorrectedCurve` metadata.
- `pumpflow/nodes/correction.py` (`:48`, `:128-134`):
  - enable the checkbox; remove the "library TODO" tooltip;
  - show B, C_Q, C_H and C_η read-only;
  - warn outside the validity range.
- Report: when viscosity is applied, list the factors in the test summary; `.po` en/pt.
- Remove the placeholder `viscosity_correction_factors` reliance: the reference notebook stays as is, but gets a markdown note pointing to `pump.viscosity`.

## Reuse
- `PerformanceCurve.to_speed` / `to_fluid` patterns (`pump/performance_curve.py:441`, `:512`), which return new instances.
- `STANDARD_UNITS["kinematic_viscosity"]` (S1); `Fluid.viscosity`.

## Tests
`tests/test_viscosity.py`:
- **Authoritative pin:** the worked example from HI 9.6.7 / ISO TR 17766 (inputs plus expected B, C_Q, C_H, C_η), supplied by the owner. Assert to the precision printed in the standard.
- B ≤ 1 → factors are exactly 1.
- B > 40 → warning or `ValueError`, matching the policy.
- `to_viscous` returns a new object and the original is unchanged.
- Water at test temperature with `apply_viscosity` → no change. B-34004A, wash water 0.52 cSt, gives B < 1, so its results are unchanged.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
- Viscosity is ✅ in the registry and the README roadmap item is closed.
- Changelog bullet; tracker ticked; one commit.

## Assumes
- Sprints 1–8 are done.
- **Owner input:** the HI 9.6.7 (or ISO TR 17766) worked example values and confirmation of the equations above. **Without them the sprint is BLOCKED.** Do not pin tests to unverified numbers.
