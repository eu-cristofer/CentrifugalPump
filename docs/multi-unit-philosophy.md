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
