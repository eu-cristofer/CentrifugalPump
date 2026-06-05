# ADR 0002 — Fix the `pint` `NameError` in the units foundation

- **Status:** Proposed
- **Criticality:** 🔴 Critical
- **Date:** 2026-06-05
- **Related:** [Architecture §4.2](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)

## Context

[`pump/utilities/unit_conversion.py`](../../pump/utilities/unit_conversion.py)
imports only:

```python
from pint import UnitRegistry, Quantity
```

…but its exception handler references the **module** name `pint`:

```python
except pint.UndefinedUnitError:        # NameError: name 'pint' is not defined
    raise ValueError(...)
except pint.DimensionalityError as e:
    raise ValueError(...)
```

The name `pint` is never bound. If an invalid unit or an incompatible conversion
ever reaches this `try`, Python raises `NameError` **instead of** the intended
`ValueError`, masking the real cause. This is in the foundation layer that every
quantity in both packages flows through (`quantity_factory`).

## Decision

Import the exception classes (or the module) explicitly and catch the correct
types. Minimal fix:

```python
from pint import UnitRegistry, Quantity
from pint.errors import UndefinedUnitError, DimensionalityError
...
except UndefinedUnitError:
    raise ValueError(f"Invalid unit: {quantity.units}")
except DimensionalityError as e:
    raise ValueError(f"Incompatible unit conversion: {e}")
```

Add a unit test that drives an incompatible conversion through
`quantity_factory` and asserts a `ValueError` (not `NameError`) is raised.

## Consequences

**Positive**
- Error reporting in the units core becomes correct and debuggable.
- Trivial, low-risk change with an obvious test.

**Negative**
- None of note.

**Note**
- This bug is latent today because the happy path returns before the handler is
  reached; it surfaces only on bad input. That makes it exactly the kind of
  defect ADR 0001's tests should lock down.
