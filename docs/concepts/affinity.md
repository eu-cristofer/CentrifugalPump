# Affinity laws

How a pump's curve changes with **speed** (a VFD, or a test run at a slightly
different speed than rated) and with **impeller diameter** (a trim).  The library
applies them in `PerformanceCurve.to_speed` and `PerformanceCurve.to_diameter`.

## The laws

For a speed change from $N_1$ to $N_2$ (same fluid, same impeller):

$$
\frac{Q_2}{Q_1} = \frac{N_2}{N_1}, \qquad
\frac{H_2}{H_1} = \left(\frac{N_2}{N_1}\right)^2, \qquad
\frac{P_2}{P_1} = \left(\frac{N_2}{N_1}\right)^3, \qquad
\eta_2 = \eta_1
$$

For an impeller trim from $D_1$ to $D_2$ (same speed) the same laws hold with the
diameter ratio $D_2/D_1$ in place of the speed ratio.

| Quantity | Symbol | Library unit |
|---|---|---|
| Capacity | $Q$ | m³/h |
| Head | $H$ | m |
| Breaking power | $P$ | kW |
| Efficiency | $\eta$ | % |
| Speed | $N$ | rpm |
| Impeller diameter | $D$ | mm (any length unit is accepted) |

## Finding the speed or diameter for a duty

A duty point $(q, h)$ does not lie on the original curve.  Along the *affinity
parabola* $H = (h/q^2)\,Q^2$ every point keeps the same $H/Q^2$, so the speed (or
diameter) that makes the curve pass through the duty follows from the intersection
$Q_1$ of that parabola with the fitted head curve:

$$
\frac{N_{new}}{N_{ref}} = \frac{D_{new}}{D_{ref}} = \frac{q}{Q_1}
$$

`pump.trim.affinity_intersection` returns $Q_1$, `pump.trim.diameter_for_duty` the
diameter, and `pump.catalogue.Catalogue.select` uses the same parabola for the speed
and trim candidates of a pump selection.

## Assumptions

- The efficiency is taken as invariant.  This is the textbook approximation; it
  degrades for large changes.
- `to_diameter` warns when the diameter changes by more than 5 % (`max_trim`).  HI-style
  corrections for large trims are out of scope.
- Measured Head and $\eta$ are *pinned* on the points (`_head`, `_efficiency`), so a
  transform scales the measured values instead of re-deriving them from pressures that
  the corrected points no longer carry.
- Transforms always return **new** curves; the original is never modified.
- The raw test points of a performance test are logged at slightly varying speeds, so a
  round trip $N_0 \to N \to N_0$ is exact only for a single-speed curve.

## Worked notebooks

- [UC-06 - affinity speed change](../../use_cases/UC-06_affinity_speed_change.ipynb)
- [UC-07 - impeller trim](../../use_cases/UC-07_trim.ipynb)
- [UC-01 - pump selection](../../use_cases/UC-01_selection.ipynb)

## API

See the {doc}`API reference <../api/pump>`: `pump.PerformanceCurve.to_speed`,
`pump.PerformanceCurve.to_diameter`, `pump.trim`.  In the workbench the formula is
available as a tooltip (`pumpflow/explain.py`).
