# ADR 0008 — Separate node logic from Qt dialogs

- **Status:** Proposed
- **Criticality:** 🟡 Medium
- **Date:** 2026-06-05
- **Related:** [Architecture §4.8](../ARCHITECTURE.md#4-coupling-dependencies--risk-spots)
- **Depends on:** [ADR 0001](0001-establish-automated-test-harness.md)

## Context

Each `pumpflow` node class is **both** dataflow logic and UI. For example
[`report_export.py`](../../pumpflow/nodes/report_export.py) mixes a small
`compute()` with a ~150-line `create_dialog()` that builds Qt widgets, wires
signals, and defines export callbacks — all in one class.

Consequences today:
- Node **logic cannot be unit-tested** without a running `QApplication` (PySide6
  imports at module load).
- The single-responsibility boundary is blurred; `compute()` correctness is
  entangled with widget construction.

## Decision

Split each node into two collaborating pieces:

1. **A pure logic object** (`compute()`, `to_signal()`, validation, settings
   schema) with **no PySide6 import** — importable and testable headless.
2. **A dialog/view builder** that depends on the logic object and lives behind the
   Qt import, constructed only when `create_dialog()` is called.

Keep `BaseNode` as the logic base; move dialog helpers (`nodes/ui.py`) and
`create_dialog` into a thin view companion. The registry continues to wire them.

## Consequences

**Positive**
- Node `compute()` logic gets covered by ADR 0001's tests without PySide6.
- Clearer SRP; UI changes stop risking logic.

**Negative**
- More files / indirection per node.
- Mechanical but broad change across seven nodes — do it incrementally, one node
  at a time, each behind a test.

## Acceptance

- At least the validation/`compute` paths of every node are tested without a
  `QApplication`.
