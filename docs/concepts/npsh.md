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

## The margin rule is data, and is not configured

No public API 610 / N-553 margin value was found, so the shipped rule is **not
configured**: `check_npsh` reports ratio and margin with the status `info`, never a
pass or fail.  When the owner enters a rule (`min_ratio` and/or `min_margin`) the status
becomes `pass` or `fail`, and a rule that is not verified is labelled *unverified
criteria* in the report.  See {doc}`acceptance-tolerances`.

API 610 itself gives the NPSHr test a 0 % positive tolerance: the tested NPSH3 must
not exceed the quoted value.

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
