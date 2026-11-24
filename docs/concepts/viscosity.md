# Viscosity correction (HI 9.6.7)

A pump tested on water performs differently on a viscous liquid: less head and
efficiency, more power.  `PerformanceCurve.to_viscous` corrects a water curve with the
Hydraulic Institute method (ANSI/HI 9.6.7, ISO TR 17766).

## Equations

At the water best-efficiency point (BEP-W), with $\nu$ in cSt, $H$ in ft **per stage**, $Q$
in gpm and $N$ in rpm:

$$
B = \frac{26.6\,\nu^{0.5}\,H^{0.0625}}{Q^{0.375}\,N^{0.25}}
$$

$$
C_Q = 2.71^{-0.165\,\log_{10}(B)^{3.15}}, \qquad
C_H = 1 - (1 - C_Q)\left(\frac{Q}{Q_{BEP}}\right)^{0.75}, \qquad
C_\eta = B^{-0.0547\,B^{0.69}}
$$

Each point of the water curve becomes $Q\,C_Q$, $H\,C_H(Q/Q_{BEP})$ and $\eta\,C_\eta$;
the breaking power is recomputed from the viscous density,
$P = \rho\, g\, Q_{vis}\, H_{vis}/\eta_{vis}$.  At the BEP $C_H = C_Q$, and at shut-off
$C_H = 1$.

| Symbol | Meaning | Library unit |
|---|---|---|
| $\nu$ | kinematic viscosity of the liquid | cSt (a dynamic viscosity is divided by the density) |
| $B$ | the method's dimensionless parameter | - |
| $C_Q, C_H, C_\eta$ | capacity, head and efficiency factors | - |

## Assumptions and validity

- Valid for $1 < B < 40$.  For $B \le 1$ there is no correction (the result equals a
  density-only change, `to_fluid`); for $B \ge 40$ the library warns that the factors are
  extrapolated.
- The speed is that of the curve's points; with several stages the head per stage enters
  $B$ (`stages=`).
- **The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by a secondary source.**  They
  were cross-checked independently (the SI and US constants agree, the factors are
  continuous at $B = 1$, the method reproduces the legacy chart), but **not** against the
  standard text.  Confirm against the purchased standard before relying on a result for
  acceptance.
- P-9001A on wash water (0.52 cSt) has $B \le 1$, so the correction leaves it
  bit-identical.

## Worked notebook

[Viscosity HI 9.6.7](../../use_cases/viscosity_HI967.ipynb): B and the factors for a 100 cSt oil
(checked by hand), the corrected curve and BEP, the $B \le 1$ identity, the effect of the
number of stages and the $B \ge 40$ warning.

## API

{doc}`API reference <../api/pump>`: `pump.viscosity` (`b_parameter`, `correction_factors`),
`pump.PerformanceCurve.bep`, `pump.PerformanceCurve.to_viscous`.  The Correction node of the
workbench shows $B$ and the factors, with the formula as a tooltip.
