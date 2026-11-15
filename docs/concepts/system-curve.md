# System curve and operating point

The **system curve** is the head the piping needs as a function of flow.  The **operating
point** is where the pump curve meets it.

## System curve

$$
H_{sys}(Q) = H_{static} + k\, Q^n
$$

- `SystemCurve(static_head, k, exponent=2)` takes $k$ with units $\mathrm{m}/(\mathrm{m^3/h})^n$
  (any equivalent unit, for example ft/gpm², is accepted and normalised).
- `SystemCurve.from_points((q1, h1), (q2, h2), exponent)` solves $H_{static}$ and $k$ through two
  points.

For a pipe run the full **Darcy-Weisbach** law is evaluated at every flow
(`SystemCurve.from_pipe`, a `PipeSystemCurve`):

$$
H_{sys} = H_{static} + \left(f\,\frac{L}{D} + \sum K\right)\frac{V^2}{2g}, \qquad
V = \frac{Q}{\pi D^2/4}, \qquad Re = \frac{V D}{\nu}
$$

The friction factor is the **Swamee-Jain** explicit approximation of Colebrook
(Swamee and Jain, 1976),

$$
f = \frac{0.25}{\left[\log_{10}\!\left(\dfrac{\varepsilon/D}{3.7} + \dfrac{5.74}{Re^{0.9}}\right)\right]^2}
$$

stated valid for $5\times10^3 \le Re \le 10^8$ and $10^{-6} \le \varepsilon/D \le 10^{-2}$, and
$f = 64/Re$ (Hagen-Poiseuille) for $Re < 2300$.  The two branches are not blended across the
transition region.  `PipeSystemCurve.equivalent(q_ref)` returns the $H_{static} + k Q^2$ curve that
matches the pipe at a reference flow.

| Symbol | Meaning | Unit |
|---|---|---|
| $L, D, \varepsilon$ | pipe length, inside diameter, roughness | m (any length unit) |
| $\sum K$ | sum of the minor-loss coefficients | - |
| $\nu$ | kinematic viscosity (from the fluid) | cSt |

## Operating point

$$
H_{pump}(Q^*) = H_{sys}(Q^*)
$$

`pump.operating_point.operating_point(pump_curve, system_curve, method="poly")` brackets the
first sign change of $H_{pump} - H_{sys}$ on a grid over $[0, 1.5\,Q_{max}]$ and refines it
by bisection (`pump.fitting.bisect_root`).  The pump head is the fitted polynomial
(`"poly"`, the API 610 primary fit) or a natural cubic spline through the test points
(`"spline"`).  The result carries $Q^*$, $H^*$, the power and the efficiency at $Q^*$.

## Assumptions

- The solution is flagged **extrapolated** when $Q^*$ lies outside the tested capacity range;
  treat it with caution.
- If the curves never meet inside the search range the function raises `ValueError`.
- The first intersection is returned; a system curve below the pump's shut-off head always
  crosses it.
- Overlaying the system curve on the Performance Plot / Explorer of the workbench is not
  implemented yet.

## Worked notebook

[UC-03/04 - system curve and operating point](../../use_cases/UC-03-04_system_operating_point.ipynb)

## API

{doc}`API reference <../api/pump>`: `pump.system_curve` (`SystemCurve`, `PipeSystemCurve`),
`pump.operating_point`, `pump.fitting`.  The workbench has *System Curve* and *Operating Point*
nodes, with the formula as a tooltip.
