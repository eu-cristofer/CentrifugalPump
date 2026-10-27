# ADR 0006 — Replace `hasattr` duck-typing with an explicit schema

- **Status:** Proposed
- **Criticality:** 🟡 Medium
- **Date:** 2026-06-05
- **Related:** [Architecture §4.6](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)
- **Depends on:** [ADR 0005](0005-consolidate-point-hierarchy.md)

## Context

Both packages use dynamically-set attributes (kwargs → `setattr` in
`BasePoint`/`Fluid` constructors) guarded by `hasattr(...)` checks scattered
through the code:

```python
if hasattr(self, "breaking_power"): ...
f"{getattr(point, 'breaking_power', 0):...}" if hasattr(point, "breaking_power") else "N/A"
```

There is no declared schema, so a **misspelled attribute silently degrades** to
`"N/A"` or `0` instead of erroring. The codebase already contains evidence of
this fragility: `"Head Shuttoff"` and `"Hydralic Power"` typos in
`performance_curve.py`, and `"utilites"` in `report.py` docstrings.

## Decision

Move from open-ended `kwargs` + `hasattr` toward **explicit, typed optional
fields**:

1. Declare the known optional quantities on the point classes (e.g.
   `breaking_power: Optional[Q_] = None`, `head_shutoff`, `inlet_pressure`, …)
   rather than accepting arbitrary kwargs.
2. Replace `hasattr(x, "y")` checks with explicit `x.y is not None` tests.
3. Keep a single, documented extension point if free-form properties are still
   wanted (e.g. an `extras: dict`), so typos can't masquerade as first-class
   attributes.
4. Add `__slots__` or a validation step if practical to reject unknown names.

## Consequences

**Positive**
- Typos fail loudly at construction instead of silently producing `"N/A"`.
- IDEs/type-checkers can see the fields; enables `mypy` (README TODO #4).
- Self-documenting API.

**Negative**
- Reduces the "anything goes" flexibility of the current `kwargs` design; any
  legitimate dynamic property must be added deliberately.
- Broader change surface — sequence it after ADR 0005 consolidates the hierarchy.
