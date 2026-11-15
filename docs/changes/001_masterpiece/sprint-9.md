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
`tests/test_viscosity.py`. There is no freely available official worked example: the HI and ISO texts are paid, and public pages only show "assumed" chart factors. The method is therefore pinned by **independent checks**, researched and computed on 2026-11-15:

1. **Published constants agree across unit systems.** B from the US form (26.6, gpm / ft / rpm / cSt) equals B from the SI form (16.5, m³/h / m / rpm / cSt) for the same pump within 0.5 %. The residual of 0.40 % is the rounding of the published constants. Check four pumps:
   - (100 cSt, 50 m, 200 m³/h, 1750 rpm)
   - (647 cSt, 45.72 m, 113.56 m³/h, 1750 rpm)
   - (1000 cSt, 100 m, 50 m³/h, 3550 rpm)
   - (20 cSt, 333.8 m, 9.8 m³/h, 10212 rpm)

   The implementation computes B in **one** unit system (US, per Eq. 3) from Pint inputs, so the SI form is only a test oracle.
2. **Continuity at B = 1.** C_Q, C_H and C_η all equal 1 for B ≤ 1 and approach 1 as B → 1⁺ (|1 − C| < 1e-6 at B = 1 + 1e-6).
3. **Legacy-chart agreement.** The old HI chart field example (McNally Institute) is 500 gpm, 3000 SSU (≈ 648 cSt), 150 ft, with chart values C_Q 0.80 and C_H 0.81.
   - At 1750 rpm the B-method gives B 13.92, C_Q 0.778, C_H(BEP) 0.778.
   - At 3550 rpm it gives B 11.67, C_Q 0.817, C_H 0.817.
   - Assert that both speeds land within ±0.05 of the chart values. This shows that the equations reproduce the legacy data the method was fitted to.
4. **Hand values.** For B = 13.92 (above), check C_Q = 2.71^(−0.165·(log10 B)^3.15) = 0.778 ± 0.002 and C_η = B^(−0.0547·B^0.69) = 0.412 ± 0.002. Also check C_H at Q/Q_BEP = 0.6 / 0.8 / 1.2 using C_H = 1 − (1 − C_Q)(Q/Q_BEP)^0.75.
5. B ≥ 40 → `UserWarning` ("outside method validity"); the factors are still returned.
6. `to_viscous` returns a new object and the original is unchanged.
7. Water at the test temperature with `apply_viscosity`, or B-34004A (0.52 cSt), gives B < 1, so there is no change, bit-identical.

**Equation source.** The equations are ANSI/HI 9.6.7-2010 Eq. 2–7 as reproduced by midstreamcalculator.com (pump viscosity correction calculator, which cites the equation numbers):
- B (US) = 26.6·ν^0.5·H^0.0625/(Q^0.375·N^0.25);
- C_Q = 2.71^(−0.165·(log10 B)^3.15);
- C_BEP-H = C_Q;
- C_H = 1 − (1 − C_Q)(Q/Q_BEP)^0.75;
- C_η = B^(−0.0547·B^0.69);
- valid for 1 < B < 40.

Docstrings cite this, state that the equations were cross-checked (checks 1–4) but **not against the standard text**, and recommend confirming against the purchased standard.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/B-34004A_MRT_reference.pumpflow --out /tmp/b34004 --formats docx,tex,pdf
```

## Definition of done
- Viscosity is ✅ in the registry and the README roadmap item is closed.
- Changelog bullet; tracker ticked; one commit.

## Assumes
Sprints 1–8 are done. The owner-input requirement was **resolved by research** on 2026-11-15; see the Tests section for the equation source and the independent validation that replaces the official worked example.
