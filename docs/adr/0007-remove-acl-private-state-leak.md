# ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`

- **Status:** Proposed
- **Criticality:** 🟡 Medium
- **Date:** 2026-06-05
- **Related:** [Architecture §4.7](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)
- **Depends on:** [ADR 0009](0009-promote-mathx-into-pump-library.md)

## Context

[`pumpflow/binding.py`](../../pumpflow/binding.py) is the project's
Anti-Corruption Layer and is otherwise clean. But `correct_curve` works around the
library's **single-fluid-per-curve** constraint by pinning **private** attributes
onto library objects:

```python
kwargs = {"_head": Q_(head, "m"), "breaking_power": Q_(r.power_kw, "kW")}
if eff is not None:
    kwargs["_efficiency"] = Q_(eff, "percent")
points.append(TestPoint(fluid=test_fluid, ..., **kwargs))
```

Per-row water density varies, but `PerformanceCurve` accepts only one `Fluid`;
so head/efficiency are computed per row and pinned via the underscored
`_head`/`_efficiency` cache fields. This couples the UI to library internals —
exactly the leak an ACL exists to prevent. It is documented as deliberate, but it
is brittle: if the library changes how it caches, the UI breaks silently.

## Decision

Close the leak from the **library side**, then simplify the binding:

1. In `pump`, add a **public** way to express the two needs:
   - per-point fluid (or per-point density) on `TestPoint`, **or**
   - an explicit public setter/constructor arg for measured head/efficiency
     (so the UI stops touching `_head`/`_efficiency`).
2. Once available, rewrite `binding.correct_curve` to use the public API and
   delete the private pinning.
3. Add a binding-level test asserting corrected curves match the previous numeric
   output (no behavioural change).

## Consequences

**Positive**
- The ACL stops depending on `pump` internals; the boundary becomes truly clean.
- The single-fluid workaround documented in the pumpflow README disappears.

**Negative**
- Requires a coordinated library change first (hence the dependency on ADR 0009
  / a library API addition). Until then, keep the current workaround but cover it
  with a regression test so a library change can't break it unnoticed.
