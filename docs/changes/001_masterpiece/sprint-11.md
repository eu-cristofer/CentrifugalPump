# Sprint 11 — UC-03 System curve + UC-04 Operating point

## Goal
- Define a system resistance curve.
- Intersect it with the pump curve to get the operating point, with flags when the solution lies outside the tested range.
- Overlay both in the plot and the Explorer.

## Files
- **ADR-0009 (promote `mathx` into `pump`).** Move `pumpflow/mathx.py` `NaturalCubicSpline` and `r_squared` into `pump/fitting.py`.
  - `pumpflow/mathx.py` re-exports them for compatibility.
  - Set ADR-0009 status to Accepted.
- `pump/system_curve.py` (new):
  - `SystemCurve(static_head, k, exponent=2)`, giving H(Q) = H_static + k·Q^n with Pint units consistent;
  - constructor `from_points((q1,h1),(q2,h2), exponent=2)`;
  - constructor `from_pipe(static_head, length, diameter, roughness, fluid, minor_k_sum)` using Darcy–Weisbach with the Swamee–Jain friction factor (cite formula sources in the docstring);
  - `head(q)`; `curve(q_array)`.
- `pump/operating_point.py` (new):
  - `operating_point(pump_curve, system_curve, method="poly"|"spline") -> OperatingPoint(q, h, power, efficiency, extrapolated: bool)`;
  - root-finding by bracketed bisection on `pump_head(q) − system_head(q)` over [0, 1.5·Q_max_tested]; implement it in `pump/fitting.py` as `bisect_root` (`pyproject.toml` has no SciPy, so do not add it);
  - `extrapolated` is set when q is outside [Q_min, Q_max] tested;
  - raise a clear error when there is no intersection.
- `pumpflow/signals.py`: `SystemCurveSpec` and `OperatingPointResult`.
- `pumpflow/nodes/system_curve.py` (new node): three modes (static + k / two points / pipe data), all `UnitField`s.
- `pumpflow/nodes/operating_point.py` (new node):
  - inputs FittedModel + SystemCurveSpec;
  - outputs the result;
  - status shows Q, H, η and the extrapolation flag.
- `pumpflow/nodes/performance_plot.py` and `explore_plot.py`: optional SystemCurveSpec / OperatingPointResult inputs drawn as overlay plus a marker.
- Register the nodes in `registry.py`.

## Reuse
- `NaturalCubicSpline` (after the move), `PerformanceFitter.head_coeffs` / `np.polyval` (`pump/performance_curve.py`).
- `ExploreChartNode` overlay (`pumpflow/nodes/explore_plot.py`).
- `Fluid` kinematic viscosity (S1) for the Reynolds number.

## Tests
- `tests/test_system_curve.py`:
  - `from_points` recovers k;
  - `from_pipe` against a hand Darcy–Weisbach calculation (water 20 °C, L = 100 m, D = 100 mm, ε = 0.045 mm, Q = 50 m³/h);
  - units mixing (gpm/ft) gives the same result.
- `tests/test_operating_point.py`:
  - analytic intersection (quadratic pump curve vs quadratic system) to 1e-6;
  - extrapolation flag;
  - no-intersection error.
- Existing spline tests still pass through the re-export.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/p9001 --formats docx,tex,pdf
```

## Definition of done
- UC-03 and UC-04 ✅ in the registry.
- ADR-0009 Accepted.
- Changelog bullet; tracker ticked; one commit.

## Assumes
Sprints 1–10 are done.
