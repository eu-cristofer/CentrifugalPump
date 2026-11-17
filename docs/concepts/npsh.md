# NPSH

Net Positive Suction Head compares what the **system** offers at the suction
($NPSH_a$) with what the **pump** needs ($NPSH_r$) to avoid cavitation.

## NPSH available

$$
NPSH_a = \frac{p_{s,abs} - p_v}{\rho\, g} + \frac{v_s^2}{2\, g} + z_s
$$

| Symbol | Meaning | Unit |
|---|---|---|
| $p_{s,abs}$ | suction pressure, **absolute** (gauge + atmosphere) | any pressure unit |
| $p_v$ | vapour pressure of the liquid at its temperature | kPa (absolute); `pump.Water` provides it from IAPWS-IF97 |
| $\rho$ | liquid density | kg/m³ |
| $v_s$ | suction velocity, $Q / (\pi D^2/4)$ | m/s (zero without the suction ID) |
| $z_s$ | elevation of the pressure tap above the pump reference | m |

The result is a length in metres.  `pump.npsh.npsh_available` takes a `pump.Pressure`
so the gauge or absolute reference is never ambiguous.

## NPSH required, NPSH3 and the margin

- **NPSH3** is the NPSHa at which the head has dropped by 3 % in a suction sweep at a fixed
  flow (`npsh3_from_sweep`): the reference head is the mean of the first two points and
  the crossing is found by linear interpolation.
- **NPSHr** versus flow is a least-squares polynomial (`NPSHrCurve`, degree 2 by
  default) of the NPSHr points.  It flags a flow outside the tested range as
  *extrapolated*.
- The **margin** is the ratio $NPSH_a/NPSH_r$ and the difference $NPSH_a - NPSH_r$
  (`npsh_margin`).

## Two different rules

1. **Rated NPSH +0 % (API 610).**  The NPSH3 tested at the rated point must not exceed
   the *quoted* NPSHr (8th ed. Table 4-2 and 4.3.4.1.3; 11th ed. Table 16 and 8.3.4.3.4).
   Every edition ships `npshr_tol_plus = 0.0`.  The rule is judged when the quoted value is
   entered: tick *Judge against the quoted NPSHr* in the NPSH node, or pass
   `npshr_quoted=` to `check_npsh`.
2. **NPSH margin (client).**  API 610 sets no NPSHa/NPSHr margin.  The Petrobras N-553
   rev E overlay requires, at rated flow, NPSHa - NPSHr $\ge$ 0.8 m **and**
   NPSHa/NPSHr $\ge$ 1.15 (7.3).  When the margin is below 1 m or the ratio below 1.20,
   NPSHr must be measured at every test point except shut-off (9.22 note).  Rev D words
   it differently (0.8 m or ratio 1.25, whichever is greater, over the whole range from
   minimum flow to rated flow), so check the revision named on the datasheet.

With no rule at all, `check_npsh` reports ratio and margin with the status `info`, never
pass or fail.  A rule changed in the node is labelled *unverified criteria*.  See
{doc}`acceptance-tolerances`.

B-34004A (N-553 rev E): NPSHa 2.40 m, NPSHr about 1.08 m at rated flow, so the margin is
1.32 m and the ratio 2.22.  It **passes**.

## Assumptions

- Incompressible liquid at a constant temperature in the suction pipe.
- The vapour pressure is that of the pure liquid at the stated temperature.
- The NPSHr curve is the vendor's (or the test's) curve at the tested speed.

## Worked notebook

[UC-05 - NPSH](../../use_cases/UC-05_npsh.ipynb): NPSHa from suction conditions with a hand
check, NPSHr points typed in feet and gpm, NPSH3 from a sweep, ratio, margin and verdicts
with an illustrative rule.

## API

{doc}`API reference <../api/pump>`: `pump.npsh` (`npsh_available`, `npsh3_from_sweep`,
`NPSHrCurve`, `npsh_margin`, `NPSHCriteria`, `check_npsh`, `plot_npsh`).
