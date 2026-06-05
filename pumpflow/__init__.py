"""
PumpFlow — API 610 Pump Performance Workbench (Orange-style node canvas).

A thin, reactive orchestration + visualization layer on top of the existing
``pump`` library.  The UI is built natively on PySide6 (QGraphicsView) so the
whole tool stays a small, self-contained binary with a minimal dependency tree
(PySide6 + matplotlib + numpy + the ``pump`` package), exactly as UI_SPEC §8 asks
for — without pulling in NodeGraphQt or the full Orange3 runtime.

Package layout
--------------
- ``signals``      : typed inter-widget payloads (UI_SPEC §3)
- ``binding``      : adapters that call into the ``pump`` library (UI_SPEC §4)
- ``mathx``        : NaturalCubicSpline + water-density polynomial ported from
                     the reference notebook (UI_SPEC §4 note)
- ``sample_data``  : seeded single-pump example (UI_SPEC §6.2 shape)
- ``persistence``  : .pumpflow project files + data-exchange JSON (UI_SPEC §6)
- ``canvas``       : the reactive node-graph scene/view/items
- ``nodes``        : the seven workflow widgets + their property dialogs (UI_SPEC §5)
- ``app``          : MainWindow, default pipeline, entry point
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
