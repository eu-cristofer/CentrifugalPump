# Multi-unit handling — design philosophy

`centrifugal-pump` treats units as a first-class concern. The library (`pump`) already
normalises every quantity through a fixed standard-unit table; the workbench (`pumpflow`)
builds a coherent **multi-unit interface** on top of that spine so an engineer can enter and
read data in whichever unit system they work in, while the physics layer stays deterministic.

A runnable, charted walkthrough lives in
[`examples/multi_unit_handling.ipynb`](../examples/multi_unit_handling.ipynb) — it
*demonstrates* the invariants below (it runs without Qt, since `pumpflow.units` depends only
on `pump`).

## The invariants

1. **The library owns the canonical unit.** `pump`'s `STANDARD_UNITS`
   ([pump/utilities/unit_conversion.py](../pump/utilities/unit_conversion.py)) is the only
   authority on the magnitude a stored quantity carries (capacity m³/h, head m, power kW, …).
   We never duplicate that table — conversions route back through `quantity_factory`.
2. **The GUI owns the menu of display units.** `pumpflow.units.UNIT_OPTIONS`
   ([pumpflow/units.py](../pumpflow/units.py)) maps each dimension to the display units the
   interface offers (label → Pint string), seeded so the canonical unit is always present.
3. **Display unit ≠ stored unit.** Dialogs let the user pick a display unit, but a node's
   `to_signal()` always normalises back to the standard unit via `units.to_standard()`. Every
   downstream node, plot, verdict and report therefore sees canonical magnitudes.
4. **One conversion path.** Everything goes through `quantity_factory`. The viscosity
   kinematic↔dynamic case (cSt ↔ cP, which needs density) is the single documented exception
   and lives only in `units.to_cst()`.
5. **Preset, then override.** A field's default display unit comes from the active project
   preset (`units.PREFS`: SI / US customary / custom); an explicit per-field choice wins.

## How it is wired

| Concern | Where |
|---|---|
| Canonical units, normalisation | `pump/utilities/unit_conversion.py` |
| Display-unit registry, presets, active preference | `pumpflow/units.py` (`UNIT_OPTIONS`, `PRESETS`, `PREFS`) |
| Reusable unit-aware numeric field | `pumpflow/nodes/ui.py` (`UnitField`) |
| Per-node usage (input nodes) | `pumpflow/nodes/rated_point.py`, `pumpflow/nodes/point.py` |
| Project-preset menu | `pumpflow/app.py` (the **Units** menu) |
| Preset persistence (`.pumpflow` `meta`) | `pumpflow/canvas/scene.py` (`to_dict`/`load_dict`) |

`UnitField` is the unit of reuse: a dialog declares one per quantity, drops it in with
`field.row("Capacity Q")`, and reads back either the display value or `field.standard()`
(the normalised magnitude). It replaces the per-quantity boilerplate that used to be
hand-written once per field.

## Extending it

- **A new display unit for an existing dimension** — add a `(label, pint_str)` entry to the
  relevant list in `UNIT_OPTIONS`. Optionally add it to a preset in `PRESETS`.
- **A new dimension** — add a list to `UNIT_OPTIONS` (canonical unit first); if the library
  doesn't yet normalise it, extend `STANDARD_UNITS` in `pump` first (see ADR 0002).
- **A new node that takes numeric input** — build a `ui.UnitField` per quantity and call
  `field.standard()` in `to_signal()`; you get preset defaults, per-field override, and live
  conversion for free.

## Back-compatibility

Project files written before this feature have no `meta` block; loading one resets the active
preset to the SI default. Nodes whose settings predate per-field units fall back to the
canonical unit. The shipped examples and the persistence round-trip test
([tests/test_persistence_roundtrip.py](../tests/test_persistence_roundtrip.py)) cover this.

## Pint end to end (001_masterpiece)

Project [001_masterpiece](changes/001_masterpiece/README.md) extended the philosophy above
from "normalise at the node boundary" to "a Pint quantity everywhere". The rules that now
hold:

- **Signals carry Quantities.** `RatedPoint`, `FluidSpec`, `TestRow`, `TestPointSet`,
  `PointSample` and `CorrectedCurve.target_speed` hold Pint quantities, not floats with an
  implied unit. `pumpflow/binding.py` has no unit literals for signal fields: it passes
  quantities straight into the library constructors (`pump` never accepts a raw number).
- **Gauge versus absolute pressure.** `pump.Pressure` carries a reference. A difference has
  no reference, and mixing a gauge value with an absolute one is an error rather than a
  silent offset. Pressure fields in the GUI show a **g/a** selector, and the Test Points
  table stores the reference on disk. The g/a conversion is lossless (5 decimals).
- **Schema v2 persistence.** A `.pumpflow` file stores `{"value", "unit"}` for every
  quantity, so the file says what each number means whatever the active preset. Old v1
  files are upgraded on open by a lossless, idempotent migrator (`persistence.migrate`);
  results of every shipped project are bit-identical before and after. See
  [ADR 0011](adr/0011-schema-v2-value-unit-persistence.md) and
  [UI_SPEC §10.2](UI_SPEC.md).
- **Per-column units.** The Test Points table has a unit per column. Changing a column's
  unit converts the stored values (it does not just relabel them), and pasted data may carry
  a header row such as `Q [gpm]` or `P_dis [psi g]`, so a datasheet can be entered exactly as
  printed with no hand conversion.
- **Hz versus revolution/second (a trap).** Pint's `Hz` is `1/s`, with no revolution in it,
  whereas `rpm` is `revolution/minute` and one revolution is 2π rad. Converting a speed
  through `Hz` is therefore off by 2π. Speed units must be written `revolution/second`,
  never `Hz`.
- **Compact on-disk unit spelling.** Units are always written in one compact Pint spelling,
  so a migrated file and a freshly saved one are byte-identical. Missing `*_unit` keys in
  old files take the canonical unit, never the active display preset (the latter was a
  latent gpm versus m³/h mix-up).
