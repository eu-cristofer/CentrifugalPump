# ADR 0009 — Promote `mathx` into the `pump` library

- **Status:** Proposed
- **Criticality:** 🟢 Low (numerical-fidelity risk: Medium)
- **Date:** 2026-06-05
- **Related:** [Architecture §4.9](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)

## Context

[`pumpflow/mathx.py`](../../pumpflow/mathx.py) holds two pieces of physics/maths
that conceptually belong to the engineering library, not the UI:

- `NaturalCubicSpline` — the notebook's optional secondary fit.
- `water_density_kgm3(temp_c)` — water density vs temperature, used to compute the
  Test Points grid's `Head` column.

Two problems:
1. **Layering** — the UI carries physics, so any non-UI consumer (a script, a
   future service) can't reuse it without importing `pumpflow`.
2. **Fidelity** — the water-density polynomial is a placeholder "Kell-style" fit,
   **not** the reference notebook's exact coefficients. The pumpflow README flags
   this explicitly. Head values therefore carry a small, undocumented modelling
   error versus the reference UX.

## Decision

1. Move `NaturalCubicSpline`, `water_density_kgm3`, and `r_squared` into `pump`
   (e.g. `pump/utilities/mathx.py` or a `pump.fitting` module), exported via
   `pump.__all__`.
2. Replace the placeholder water-density coefficients with the **reference
   notebook's exact values** (or a cited standard correlation).
3. Update `binding.py` and `nodes/plotting.py` to import from `pump`; delete the
   `pumpflow` copies.
4. Add tests pinning a few `water_density_kgm3` and spline values.

## Consequences

**Positive**
- Physics lives in the library; the UI shrinks toward pure orchestration.
- Head/efficiency numbers match the reference notebook (closes a fidelity gap).
- Enables ADR 0007 (the spline/density become library citizens).

**Negative**
- Coordinated move across two packages; do it with the imports updated in one
  change and the tests green.
