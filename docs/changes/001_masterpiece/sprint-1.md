# Sprint 1 — Library quantity spine

## Goal
`pump` can represent every quantity the workbench needs as a Pint quantity, with one serialisation path. This covers:
- kinematic viscosity;
- gauge/absolute pressure;
- standard gravity;
- water viscosity and vapour pressure;
- JSON value+unit pairs.

This sprint makes no GUI changes and changes no numbers in existing results, beyond the gravity constant noted below.

## Files
- `pump/utilities/unit_conversion.py`:
  - add a `kinematic_viscosity` dimensionality → `cSt` to `STANDARD_UNITS`;
  - keep pressure contexts as they are.
- `pump/constants.py` (new): `G = Q_(9.80665, "m/s**2")`, `P_ATM = Q_(101325, "Pa")`.
- `pump/utilities/pressure.py` (new):
  - `Pressure` frozen dataclass: `value: Quantity`, `reference: Literal["g","a"]`, `atmosphere: Quantity = P_ATM`;
  - methods `absolute()`, `gauge()`, `__sub__` (difference is reference-free when both share the same atmosphere), `to_json()`/`from_json()`.
- `pump/utilities/fluid.py`, `Water`:
  - add `kinematic_viscosity` (moved from `pumpflow/binding.py:97-113`: `water_dynamic_viscosity_cP` and `water_kinematic_viscosity_cst`);
  - add `vapour_pressure` (a published saturation correlation valid 0–200 °C, for example Wagner–Pruss / IAPWS-IF97 region 4; **cite the source in the docstring**).
- `pump/quantity_io.py` (new):
  - `to_json(q) -> {"value": float, "unit": str}`, using the `~` compact pint string so it round-trips;
  - `from_json(d) -> Quantity`, which also accepts a bare number plus a `default_unit` argument for the v1 migration in S2.
- Replace the literal `9.81` in `pump/point.py:99` (and anywhere else in `pump/`) with `G`.
- `pumpflow/binding.py`:
  - `G = 9.81` at :59 becomes `pump.constants.G` magnitude;
  - the water viscosity helpers delegate to `Water`;
  - drop the kinematic-viscosity warning suppression at :82-89 and :119-121 once `STANDARD_UNITS` knows cSt.
- Export new names via `pump/utilities/__init__.py` and `pump/__init__.py` `__all__`.

## Reuse
- `quantity_factory`, `STANDARD_UNITS`, `extract_context` (`pump/utilities/unit_conversion.py`).
- `Fluid`, `Water` (`pump/utilities/fluid.py`).
- The existing `Q_` registry. Never create a second `UnitRegistry`.

## Tests
`tests/test_quantity_spine.py`:
- `to_json`/`from_json` round-trip for capacity, head, power, pressure (psi, bar, kgf/cm², kPa), temperature (°C, °F, K), speed (rpm), viscosity (cSt, cP) and length (mm, in).
- `Pressure`:
  - 50 psi g − 10 psi g == 40 psi (reference-free);
  - 1 bar g → absolute == 2.01325 bar a;
  - mixing references raises `ValueError`.
- `Water(20 °C)`: kinematic viscosity ≈ 1.004 cSt (±1 %); vapour pressure ≈ 2.339 kPa (±1 %).
- `Water(100 °C)`: vapour pressure ≈ 101.4 kPa (±1 %).
- `quantity_factory(Q_(1, "cSt"))` returns cSt with **no warning** (`pytest.warns` not raised; use `warnings.catch_warnings` + `simplefilter("error")`).
- Doctest example in each new public function.

## Acceptance
```bash
pytest
python -m pumpflow.export_cli examples/user/P-9001A_MRT_reference.pumpflow --out /tmp/p9001 --formats docx,tex,pdf
black --check pump/constants.py pump/quantity_io.py pump/utilities/pressure.py tests/test_quantity_spine.py
```
- Branch A stays APPROVED.
- Changing g from 9.81 to 9.80665 shifts derived head by about +0.03 %. Record the new predicted H at 9.80 m³/h in the changelog bullet; it is expected near 339.5 m.

## Definition of done
- New modules are documented with doctests.
- No raw `9.81` remains (`grep -rn "9\.81\b" pump pumpflow` returns nothing).
- No kinematic-viscosity warning suppression remains in `binding.py`.
- Changelog bullet added; tracker ticked; one commit.

## Assumes
Baseline commit `2e1983a` (LaTeX/PDF export, `pumpflow/export_cli.py`, P-9001A reference project, `tests/test_report_formats.py`) is present on `feat/masterpiece`.
