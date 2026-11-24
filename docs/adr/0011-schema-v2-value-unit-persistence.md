# ADR 0011 — Schema v2: value + unit persistence

- **Status:** Accepted
- **Criticality:** 🟠 High
- **Date:** 2026-11-14
- **Related:** [ADR 0002](0002-fix-pint-nameerror-in-units-core.md),
  [multi-unit philosophy](../multi-unit-philosophy.md),
  [UI_SPEC §10.2](../UI_SPEC.md), sprint 2b and sprint 3 of
  [001_masterpiece](../changes/001_masterpiece/README.md)

## Context

Before 001_masterpiece, a `.pumpflow` file stored plain magnitudes with an implied unit:
a number was "in the canonical unit" or in whatever the node's `*_unit` display label said,
and nodes whose settings predated per-field units silently fell back to the active project
preset. This had three problems:

1. **Ambiguity.** A bare `9.8` could be m³/h or gpm depending on the preset in force when
   the file was opened. A latent gpm/m³/h mix-up existed in the migration path.
2. **No audit trail.** A FAT witness entering a datasheet in gpm, psi g and °F could not
   see that again in the saved file.
3. **Mismatch with the runtime.** Signals and library constructors now carry Pint
   quantities, so the persistence layer was the last place that dropped units.

## Decision

- Every quantity in a `.pumpflow` document is stored as `{"value": <magnitude>, "unit":
  "<pint unit>"}`, and `meta.schema_version` is 2. The Test Points table stores a unit per
  column and a pressure reference (gauge or absolute).
- Translation between runtime settings (flat floats plus `*_unit` labels) and the v2 shape
  happens only at the persistence boundary, in `pumpflow/settings_codec.py`
  (`encode`/`decode`, driven by a per-kind field table). Kinds not in the table pass through.
- `persistence.migrate` upgrades v1 documents on open. It is pure, idempotent and lossless:
  magnitudes are never perturbed when the unit does not change, and a missing `*_unit` key
  takes the canonical unit, never the active preset. All shipped projects evaluate
  bit-identically after migration.
- Units are written in one compact Pint spelling so that a migrated file and a freshly
  saved one are byte-identical. Unset optional quantities are stored as `null` with no
  stray `*_unit` key. Speed units use `revolution/second`, never `Hz`.
- The data-exchange JSON (UI_SPEC §6.2) is unchanged.

## Consequences

- **Positive:** files are self-describing and unit-safe; the same file opens identically
  under any display preset; new node kinds get persistence by registering their fields in
  the codec; v1 files keep working without manual steps.
- **Negative:** files are larger and less hand-editable; a node kind that is not registered
  in the codec loses its units on save (guarded by a regression test after the S11
  system-curve entry was found in the wrong table); the migrator must be kept for as long
  as v1 files exist.
- **Neutral:** user files in `examples/user/` that are still v1 are left untouched and
  still evaluate identically.

## Alternatives considered

1. **Keep plain magnitudes plus per-field `*_unit` keys.** Rejected: leaves the
   preset-fallback ambiguity and needs a unit key beside every number.
2. **Store everything in canonical units only.** Rejected: loses how the engineer entered
   the data (gpm, psi g, hp), which matters for witnessing and re-entry.
3. **Store Pint's own serialisation (pickle or `Quantity` JSON).** Rejected: not stable
   across Pint versions and not human-readable.
