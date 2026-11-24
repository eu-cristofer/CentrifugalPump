# ADR 0003 — Correct the Python version floor metadata

- **Status:** Proposed
- **Criticality:** 🔴 Critical
- **Date:** 2026-06-05
- **Related:** [Architecture §1.2 / §4.3](../ARCHITECTURE.md#12-primary-tech-stack)

## Context

`pyproject.toml` (and `tests/pyproject.toml`) declare:

```toml
requires-python = ">=3.6"
```

The source, however, uses syntax that only exists in **Python 3.12+**:

- **PEP 701** f-strings with nested same-quote expressions, e.g.
  `f"{self._("Report")}_..."` in `report.py` and
  `f"{getattr(point, "breaking_power", 0):...}"` in `performance_curve.py`.
- `typing.Self` (3.11+).

Installing on any interpreter below 3.12 yields a `SyntaxError` at import time —
the package cannot do what its own metadata advertises. This misleads users and
breaks `pip` resolution on supported-but-incompatible environments.

## Decision

Set the floor to the version the code actually requires:

```toml
requires-python = ">=3.12"
```

Apply the change in **both** `pyproject.toml` and `tests/pyproject.toml`, and add
a one-line note to the README/installation docs. Optionally add a CI matrix entry
pinned to 3.12 to prevent regression.

### Alternative considered

Rewrite the 3.12-only syntax to support older interpreters (e.g. 3.9). Rejected:
it adds ongoing constraint for no clear user demand, and `typing.Self` plus the
f-string style are pervasive. Raising the floor is simpler and honest.

## Consequences

**Positive**
- Metadata matches reality; `pip` fails fast with a clear message on old Pythons.

**Negative**
- Drops nominal support for 3.6–3.11. In practice that support never worked, so
  no real capability is lost.
