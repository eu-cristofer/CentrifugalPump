# Head components and efficiency

The head a pump develops is measured with two pressure gauges, but it has three
components.  `pump.TestPoint` computes all of them.

## Total head

$$
H = \underbrace{\frac{\Delta P}{\rho\, g}}_{\text{pressure}}
  + \underbrace{\frac{v_d^2 - v_s^2}{2\, g}}_{\text{velocity}}
  + \underbrace{(z_d - z_s)}_{\text{elevation}}
$$

with the velocity at each tap from the flow and the pipe inside diameter,

$$
v = \frac{Q}{\pi D^2 / 4}
$$

| Symbol | Meaning | Unit used by the library |
|---|---|---|
| $\Delta P$ | discharge minus suction pressure | bar (delta context); any pressure unit is accepted |
| $\rho$ | liquid density at the measured temperature | kg/m³ |
| $g$ | standard gravity, 9.80665 | m/s² (`pump.constants.G`) |
| $Q$ | capacity | m³/h |
| $D_s, D_d$ | suction and discharge pipe inside diameters | m (any length unit) |
| $z_s, z_d$ | elevations of the two pressure taps | m (any length unit) |

## Assumptions

- A difference of two gauge (or two absolute) pressures carries no reference: it does not
  matter whether the gauges read gauge or absolute pressure, as long as both do.
  `pump.Pressure` makes the reference explicit and refuses to subtract mixed references.
- The **velocity** term needs *both* pipe diameters, and the **elevation** term needs
  *both* elevations.  A half-specified geometry is never used: the term is then zero.
  Without any geometry the head is the pressure head only.
- A measured head given explicitly overrides the computed one.
- The density is that of the test water at the *row's own* temperature, which is why a
  test sheet logs a temperature per row.

## Efficiency

$$
\eta = \frac{P_{hyd}}{P_{shaft}} = \frac{\rho\, g\, Q\, H}{P_{shaft}}
$$

$P_{shaft}$ is the breaking (motor output) power; `TestPoint.hydraulic_power` is
$\rho g Q H$.  The efficiency is expressed in percent.

## Worked notebooks

- [UC-02 - performance verification (B-34004A, native units)](../../use_cases/UC-02_performance_verification.ipynb)
  computes the head per row, the complete head with velocity and elevation, and the
  efficiency.
- [UC-00 - working in the engineer's units](../../use_cases/UC-00_utilities_demo.ipynb)

## API

{doc}`API reference <../api/pump>`: `pump.TestPoint` (`pressure_head`, `velocity_head`,
`elevation_head`, `compute_head`, `compute_hydraulic_power`, `compute_efficiency`) and
`pump.Pressure`.  In the workbench the *Head* column header of the Test Points table
and the formula tooltips use the text of `pumpflow/explain.py`.
