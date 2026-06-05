# ADR 0001 — Establish an automated test harness

- **Status:** Proposed (starter suite landed)
- **Criticality:** 🔴 Critical
- **Date:** 2026-06-05
- **Related:** [Architecture §4.1](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots), [Run & Test Tutorial §5](../RUN_AND_TEST.md#5-testing)

## Context

`pyproject.toml` lists `pytest` as a dev dependency, but the repository ships
**no automated tests** — `tests/` contained only Jupyter notebooks, which are
demos, not assertions. The library produces **safety-relevant FAT acceptance
verdicts** (APPROVED/REJECTED against API 610 tolerances). Every refactor is
currently unguarded; a silent numeric regression could pass an unacceptable pump
or fail a compliant one.

README TODO #2 already acknowledges this: *"Add testing."*

## Decision

Stand up a `pytest` harness and treat it as a **precondition for all other
refactors**. Concretely:

1. Add a fast, Qt-free **library smoke suite** pinning the core workflow:
   units canonicalization, curve fitting, `to_speed`/`to_fluid` affinity laws,
   `PerformanceChecker` tolerance bands, and headless plotting.
   *(Done — see [`tests/test_pump_smoke.py`](../../tests/test_pump_smoke.py),
   11 passing tests.)*
2. Add **regression tests** that pin expected numbers from the worked
   `examples/*.ipynb`, turning the notebooks into an executable specification.
3. Add a **separate `pytest-qt` suite** for `pumpflow` node `compute()` logic,
   isolated so it only runs where PySide6 is installed.
4. Wire the suite into CI (GitHub Actions) on push/PR.

## Consequences

**Positive**
- Refactors in ADRs 0004–0009 become safe to attempt.
- Numeric behaviour is documented as code, not prose.
- New contributors get a fast feedback loop.

**Negative / cost**
- Node-logic tests require a `QApplication`; keep them isolated to avoid making
  the core suite depend on PySide6.
- Writing example-regression fixtures takes effort to extract "golden" numbers.

**Follow-ups**
- The suite should eventually assert the bugs in ADR 0002 and 0005 are fixed
  (currently they would fail if exercised).
