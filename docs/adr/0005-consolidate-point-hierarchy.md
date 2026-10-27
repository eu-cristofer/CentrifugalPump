# ADR 0005 — Consolidate the `Point` hierarchy & remove broken code

- **Status:** Proposed
- **Criticality:** 🟠 High
- **Date:** 2026-06-05
- **Related:** [Architecture §4.5](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)
- **Depends on:** [ADR 0001](0001-establish-automated-test-harness.md)

## Context

[`pump/point.py`](../../pump/point.py) defines `BasePoint`, `DesignPoint`,
`Point`, and `TestPoint`. Several hydraulic properties are **copy-pasted
verbatim** across `Point` and `TestPoint` (and partly `DesignPoint`):
`pressure_head`, `inlet_velocity`, `outlet_velocity`, `velocity_head`,
`elevation_head`, `compute_head`, `head`.

This is a textbook DRY violation: a fix to one (e.g. a sign convention) must be
remembered in 2–3 places. It also hides **dead/broken code**:

```python
class Point(BasePoint):
    @property
    def outlet_pressure(self):
        return quantity_factory()   # called with no args → TypeError
```

`quantity_factory()` requires a `Quantity` argument, so this property raises
unconditionally if ever accessed.

## Decision

1. **Introduce a `HydraulicPointMixin`** (or move the shared properties up into
   `BasePoint`) holding the single canonical implementation of pressure/velocity/
   elevation/head. `Point` and `TestPoint` inherit it; `DesignPoint` overrides
   only where its semantics genuinely differ.
2. **Delete the broken `Point.outlet_pressure`** (or implement it correctly from
   `inlet_pressure` + differential, matching `DesignPoint.outlet_pressure`).
3. Add tests for each shared property on each concrete type.

## Consequences

**Positive**
- One place to change hydraulic math; eliminates a class of "fixed it in one
  subclass only" bugs.
- Removes guaranteed-`TypeError` dead code.

**Negative**
- Inheritance/MRO must be checked against the `kwargs`-driven dynamic attributes
  in `BasePoint.__init__`; do it under tests (ADR 0001).
- `DesignPoint` differs subtly (it has `differential_head`, not pressures) —
  keep its overrides explicit rather than forcing a single hierarchy.
