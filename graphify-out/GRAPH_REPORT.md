# Graph Report - .  (2026-07-10)

## Corpus Check
- 93 files · ~59,096 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 905 nodes · 1663 edges · 54 communities (42 shown, 12 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 126 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- tests
- pumpflow
- pumpflow
- pump
- pumpflow
- pump
- pump
- pumpflow
- pump
- pump
- pumpflow
- tests
- pump
- pumpflow
- pumpflow
- pump
- pumpflow
- pump
- tests
- pumpflow
- pumpflow
- pump
- pumpflow
- tests
- pumpflow
- pumpflow
- pumpflow
- docs
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- pumpflow
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 52
- Community 53

## God Nodes (most connected - your core abstractions)
1. `quantity_factory()` - 41 edges
2. `BaseNode` - 40 edges
3. `MainWindow` - 32 edges
4. `TestPoint` - 28 edges
5. `PerformanceCurve` - 24 edges
6. `PerformanceChecker` - 24 edges
7. `Fluid` - 24 edges
8. `PortItem` - 23 edges
9. `PortSpec` - 23 edges
10. `DesignPoint` - 22 edges

## Surprising Connections (you probably didn't know these)
- `docs/sprints/README.md` --references--> `Sprint system`  [AMBIGUOUS]
  docs/sprints/README.md → graphify-out/.graphify_chunk_03.json
- `docs/product/use-cases.md` --conceptually_related_to--> `pump/performance_curve.py`  [EXTRACTED]
  docs/product/use-cases.md → pump/performance_curve.py
- `docs/sprints/sprint-04-docstrings-doctests.md` --references--> `pump/utilities/unit_conversion.py`  [EXTRACTED]
  docs/sprints/sprint-04-docstrings-doctests.md → pump/utilities/unit_conversion.py
- `docs/sprints/sprint-01-test-foundation.md` --references--> `Sprint S1`  [EXTRACTED]
  docs/sprints/sprint-01-test-foundation.md → graphify-out/.graphify_chunk_03.json
- `test_quantity_factory_canonicalizes_capacity()` --calls--> `quantity_factory()`  [INFERRED]
  tests/test_pump_smoke.py → pump/utilities/unit_conversion.py

## Import Cycles
- 1-file cycle: `pump/__init__.py -> pump/__init__.py`
- 1-file cycle: `pump/utilities/__init__.py -> pump/utilities/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/test_points.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/compliance.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/markdown_note.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/report_export.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/fluid.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/correction.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/curve_fit.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/explore_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/performance_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/rated_point.py -> pumpflow/nodes/__init__.py`

## Hyperedges (group relationships)
- **PumpFlow Layered Architecture (UI -> logic -> binding -> library)** — pumpflow_app_module, pumpflow_signals_module, pumpflow_binding_module, pumpflow_persistence_module, pumpflow_units_module, pumpflow_reactive_topological_evaluation, pumpflow_binding_boundary_single_entry [EXTRACTED 1.00]

## Communities (54 total, 12 thin omitted)

### Community 0 - "pumpflow"
Cohesion: 0.05
Nodes (30): EdgeItem, QPointF, canvas.edge_item ================  A bezier link carrying a signal from an outpu, canvas package — reactive node-graph scene/view/items (PySide6)., _elide(), NodeItem, QRectF, canvas.node_item ================  The on-canvas representation of one workflow (+22 more)

### Community 1 - "pumpflow"
Cohesion: 0.06
Nodes (49): pumpflow/app.py, app ===  The PumpFlow main window: a node toolbox, the reactive canvas, the menu, run(), Run PumpFlow:  python -m pumpflow, make_node(), parse_decimal(), Parse a number that may use ``,`` or ``.`` as the decimal separator.      Heuris, json_from_signals() (+41 more)

### Community 2 - "pumpflow"
Cohesion: 0.06
Nodes (52): Exception, Liquid water at a given temperature.      Density is computed from a 4th-order p, Water, assemble_report_data(), BindingError, build_report_png(), check_compliance(), correct_curve() (+44 more)

### Community 3 - "pumpflow"
Cohesion: 0.06
Nodes (28): FluidNode, _btn(), _pick_dir(), _pick_file(), PropertyDialog, QWidget, Like row() but with a QComboBox as the suffix widget for unit selection., A consistent shell: header, a body you fill, and live-apply semantics. (+20 more)

### Community 4 - "pumpflow"
Cohesion: 0.08
Nodes (30): Figure, PumpFlow — API 610 Pump Performance Workbench (Orange-style node canvas).  A thi, PortSpec, nodes.base ==========  The Qt-agnostic logic of a widget node.  A node declares, _Fallback, nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)  Inputs ``FittedMode, nodes.curve_fit — Curve Fit  (UI_SPEC §5.4)  Input ``CorrectedCurve`` → output `, nodes.explore_plot — Performance Explorer  An *interactive* exploratory chart (p (+22 more)

### Community 5 - "pumpflow"
Cohesion: 0.08
Nodes (21): _d(), MainWindow, Path, Switch the project's display-unit preset (File-level preference)., Reflect the active ``units.PREFS`` preset in the Units menu check., Flag the session as having unsaved changes.          Appends an asterisk to the, Clear the unsaved-changes flag.          Removes the asterisk appended by :meth:, Guard destructive actions with a Save / Discard / Cancel prompt.          Presen (+13 more)

### Community 6 - "tests"
Cohesion: 0.08
Nodes (20): PerformanceChecker, A class to check and validate the performance of a system based on a design poin, Determines the shutoff head tolerance based on the design point head value., Computes the acceptable limits for head, shutoff head, and breaking power., Checks whether the performance curve values fall within the acceptable limits., Generates a summary table checking if performance values are within limits., API 610 compliance bands — UC-02 (verify pump performance / FAT).  Pins the nume, test_acceptable_limits_exposes_all_bands() (+12 more)

### Community 7 - "pumpflow"
Cohesion: 0.08
Nodes (14): ExploreChartNode, Pin every left axis to the widest one so the plot frames (and the         shared, A capacity spin-box + a table of the values each fitted polynomial         regre, A vertical guide + value label that follows the cursor across panes., _bundle_json(), Richer §7 bundle: shared rated + per-pump corrected data + verdict., Banner, combo() (+6 more)

### Community 8 - "pumpflow"
Cohesion: 0.07
Nodes (15): Access an individual TestPoint by index.          Parameters         ----------, Specialized version of the BasePoint class for handling test or operational data, Calculates the head generated due to pressure difference.          Returns, Calculates the fluid velocity at the pump outlet.          Returns         -----, Calculates the head difference due to change in fluid velocity.          Returns, Calculates the head difference due to elevation.          Returns         ------, Computes the total dynamic head (TDH) from its components.          The TDH is t, The total dynamic head of the point.          Returns a cached `_head` value if (+7 more)

### Community 9 - "pump"
Cohesion: 0.11
Nodes (15): Any, PerformanceCurve, Q_, A container for handling a collection of TestPoint objects that share the same f, Predicts the head for a given flow (capacity) using the stored polynomial., Predicts the efficiency for a given flow (capacity) using the stored polynomial., Predicts the power for a given flow (capacity) using the stored polynomial., Plots the pump performance curve with three subplots:         - Head vs. Capacit (+7 more)

### Community 10 - "pumpflow"
Cohesion: 0.11
Nodes (12): nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)  Inputs ``RatedPo, SpeedCorrectionNode, choice_options(), current_choice(), nodes.fluidpick — shared "which fluid drives this node" selection logic.  A flui, Return the chosen ``FluidSpec`` from ``specs``, or ``None`` for the node     def, ``[(label, data)]`` pairs for :func:`pumpflow.nodes.ui.combo`.      A leading de, The combo ``data`` value that should be shown selected, accounting for     the d (+4 more)

### Community 11 - "pump"
Cohesion: 0.11
Nodes (13): LocalizationHelper, Generates a report from a predefined template.          Parameters         -----, Handles translation and localization using gettext.      Parameters     --------, Add introductory section to the document.                  Parameters         --, Add design point section to the document.                  Parameters         --, Add equipment description section to the document.                  Parameters, Add test summary section to the document.                  Parameters         --, Sets up gettext for localization.          Returns         -------         Calla (+5 more)

### Community 12 - "pump"
Cohesion: 0.09
Nodes (7): BaseNode, Return ``{output_port_name: payload}``.  Override me., Return a configured ``QDialog`` (or ``None`` if the node has none)., Helper: clear outputs and show an amber/idle status (UI_SPEC §7)., Plain-JSON view of ``settings`` for ``.pumpflow`` (override if needed)., ComplianceCheckNode, MarkdownNoteNode

### Community 13 - "pumpflow"
Cohesion: 0.11
Nodes (12): Initializes the PerformanceChecker with a design point and performance curve., DesignPoint, Q_, Specific energy is the energy per unit mass of fluid.         It is calculated a, The mechanical power transferred to the liquid as it passes through the pump,, Calculates the outlet pressure based on inlet pressure and various heads., Calculates the head difference due to elevation.          Returns         ------, Calculates the fluid velocity at the pump inlet.          Returns         ------ (+4 more)

### Community 14 - "pump"
Cohesion: 0.12
Nodes (8): GraphView, QPointF, Capture the current zoom + scene-space center for ``.pumpflow`` files., Restore a zoom + center previously captured by :meth:`view_state`., Apply a multiplicative zoom about the cursor, clamped to the band., Scroll the viewport by a pixel delta (touchpad / plain wheel pan)., Frame every node in the view (zoom extents), clamped to the zoom band., QGraphicsView

### Community 15 - "pump"
Cohesion: 0.13
Nodes (16): Calculates the fluid velocity at the pump inlet.          Returns         ------, Q_, Initializes a Fluid object with converted physical properties.          Paramete, Q_, quantity_factory(), Converts a given quantity to its corresponding standard unit.          Parameter, Converts a given quantity to its standard unit. It is the entry point of     eng, Units & ``Fluid`` spec — the executable version of ``tests/utilities_test.ipynb` (+8 more)

### Community 16 - "pumpflow"
Cohesion: 0.12
Nodes (15): canonical_unit(), convert_display(), _convert_viscosity(), options_for(), _pint_str(), units — the multi-unit handling spine of the workbench =========================, The library's standard display label for a dimension (first option)., ``[(label, label)]`` pairs suitable for :func:`pumpflow.nodes.ui.combo`. (+7 more)

### Community 17 - "tests"
Cohesion: 0.16
Nodes (13): ABC, pump ====  This module provides tools for API 610 pumping system calculations., peroformance_curve ==================  This module defines the PerformanceCurve, point =====  This module defines the `BasePoint` class and its subclasses, which, This module provides a representation of fluids and their physical properties, e, utilities =========  This submodule provides unit conversion utilities to standa, extract_context(), ImprovedQuantity (+5 more)

### Community 18 - "pump"
Cohesion: 0.12
Nodes (17): docs/UI_SPEC.md, pumpflow package (__init__.py), Boundary: only pumpflow/binding.py may call into pump, pumpflow/binding.py, Data-exchange JSON format (unit/rated/points; comma or dot decimals), pumpflow/docs/architecture.md, pumpflow/docs/data_formats.md, pumpflow/docs/index.md (+9 more)

### Community 19 - "pumpflow"
Cohesion: 0.14
Nodes (10): PerformanceFitter, ndarray, Lazily computes the polynomial regression coefficients for head vs. capacity., Lazily computes the polynomial regression coefficients for efficiency vs. capaci, Lazily computes the polynomial regression coefficients for power vs. capacity., Handles polynomial regression for performance metrics (head, efficiency, power),, Lazily computes and returns the capacity values as a NumPy array.          Retur, Lazily computes and returns the head values as a NumPy array.          Returns (+2 more)

### Community 20 - "pumpflow"
Cohesion: 0.16
Nodes (9): pressure_to_pa(), _opt(), PointNode, Return a positive float, or ``None`` when blank/zero/non-numeric., ``_opt`` then normalise to the standard unit — ``None`` stays ``None``., Derive head (m) from suction/discharge pressures + fluid density., _std_opt(), PointSample (+1 more)

### Community 21 - "pump"
Cohesion: 0.14
Nodes (14): sample_project_doc() builder, Canonical single-pump {nodes, edges} document, GraphScene, load_dict, Persistence round-trip guard, Optional PySide6 tests via pytest.importorskip, Qt-free tests, QT_QPA_PLATFORM=offscreen (+6 more)

### Community 22 - "pumpflow"
Cohesion: 0.21
Nodes (12): ADR 0001 Establish an automated test harness, ADR 0004 Refactor PerformanceCurve (split plotting from computation), ADR 0005 Consolidate Point hierarchy and remove broken code, ADR 0006 Replace hasattr duck-typing with explicit schema, Anti-Corruption Layer (ACL) via pumpflow/binding.py, pump, pumpflow, docs/adr/README.md (+4 more)

### Community 23 - "pump"
Cohesion: 0.17
Nodes (8): Fluid, Returns a detailed string representation of the fluid., Returns a detailed string representation of the fluid's properties., A class to represent a fluid and its properties, enabling engineering calculatio, Returns a detailed string with fluid's properties., test_mixed_fluid_curve_is_rejected(), test_fluid_density_canonicalizes_to_kg_per_m3(), test_fluid_repr_is_stable()

### Community 24 - "tests"
Cohesion: 0.18
Nodes (12): 8-hour programming sprint, Example-driven development, Notebook demos become assertions, Single commit per sprint, One focused .md sprint file, Sprint S0, Sprint system, docs/product/audience.md (+4 more)

### Community 25 - "pumpflow"
Cohesion: 0.18
Nodes (7): NaturalCubicSpline, ndarray, r_squared(), mathx =====  Maths ported into the UI layer from the reference notebook (``pump_, Return ``(xs, ys)`` of ``n`` evenly spaced samples across the data., Coefficient of determination, R²., Natural cubic spline interpolation (second derivative = 0 at both ends).      Pa

### Community 26 - "pumpflow"
Cohesion: 0.20
Nodes (6): BasePoint, Returns a detailed string representation of the fluid's properties., Represents a system point with physical quantities.      Parameters     --------, Returns a detailed string representation of the fluid's properties., Returns a detailed string with fluid's properties., Returns a detailed string representation of the fluid's properties.

### Community 28 - "pumpflow"
Cohesion: 0.25
Nodes (8): acceptable_limits, BasePoint, DesignPoint, Core public classes with doctest examples, PerformanceChecker, PerformanceCurve, report_summary, tests/test_compliance.py

### Community 29 - "tests"
Cohesion: 0.25
Nodes (8): API 610, CentrifugalPump project, docs/product/use-cases.md, pump/utilities/unit_conversion.py, UC-00 Work in the engineer's own measurement units, UC-02 Verify pump performance (FAT), UC-06 Evaluate speed change (VFD), UC-09 Generate report

### Community 30 - "pumpflow"
Cohesion: 0.25
Nodes (8): Pytest collection guard: __test__ = False, Pytest configuration in pyproject.toml, TestPoint, Unit canonicalization, docs/sprints/sprint-01-test-foundation.md, pump/point.py, tests/conftest.py, tests/test_utilities.py

### Community 31 - "pumpflow"
Cohesion: 0.25
Nodes (8): port_color(), _append_param(), QTableWidget, _append(), QTableWidget, QTableWidget, _set_ro(), QColor

### Community 32 - "pumpflow"
Cohesion: 0.25
Nodes (7): curve(), design_point(), Shared pytest fixtures for the ``pump`` library suite.  These were originally in, Cold water at ~997 kg/m³ — the reference fluid for the suite., A small, monotonic Q×H / Q×P performance curve at 1750 rpm., Rated/design point matching the curve's rated region (833 m³/h, 73 m)., water()

### Community 33 - "docs"
Cohesion: 0.38
Nodes (7): FAT engineer priority, Sprint S1, Sprint S2, Sprint S3, UC-02, UC-06, UC-09

### Community 34 - "pumpflow"
Cohesion: 0.29
Nodes (6): matplotlib, numpy, pint, PySide6, python-docx, pytest

### Community 35 - "pumpflow"
Cohesion: 0.33
Nodes (3): ReportExportNode, BranchBundle, Everything Report Export needs from one connected pump branch.

### Community 36 - "pumpflow"
Cohesion: 0.33
Nodes (6): Affinity-law speed correction, API 610 compliance bands, to_speed, docs/sprints/sprint-02-pin-mvp-physics.md, pump/performance_curve.py, tests/test_affinity.py

### Community 37 - "pumpflow"
Cohesion: 0.33
Nodes (6): Docstring examples (>>>), Doctest modules (--doctest-modules), Import path: from pump.utilities ..., Sprint S4, docs/sprints/sprint-04-docstrings-doctests.md, pump/utilities/fluid.py

### Community 38 - "pumpflow"
Cohesion: 0.33
Nodes (3): fit_model(), Polynomial coeffs (primary) + natural cubic splines (secondary)., CurveFitNode

### Community 39 - "pumpflow"
Cohesion: 0.40
Nodes (3): FluidSpec, Relative density (SG) — the user-facing density form., A service fluid defined on its own canvas node (UC-00).      When wired into Spe

### Community 41 - "pumpflow"
Cohesion: 0.50
Nodes (4): Acceptance criteria, Definition of Done, Sprint template, Branch/commit policy (one commit)

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (3): Shared rated point/fluid + one entry per pump TAG, ready to serialize., Acceptance reflects ALL pumps (UI_SPEC §2 / §9)., ReportBundle

## Ambiguous Edges - Review These
- `docs/sprints/README.md` → `Sprint system`  [AMBIGUOUS]
  graphify-out/.graphify_chunk_03.json · relation: references

## Knowledge Gaps
- **71 isolated node(s):** `pumpflow package (__init__.py)`, `pumpflow/binding.py`, `pumpflow/mathx.py`, `pumpflow/numfmt.py`, `pumpflow/units.py` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `docs/sprints/README.md` and `Sprint system`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `quantity_factory()` connect `pump` to `tests`, `pumpflow`, `pump`, `pumpflow`, `pumpflow`, `tests`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `correct_curve()` connect `pumpflow` to `pumpflow`, `pumpflow`, `pump`, `pumpflow`, `pump`, `pump`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `BaseNode` connect `pump` to `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pumpflow`, `pump`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `quantity_factory()` (e.g. with `test_quantity_factory_canonicalizes_capacity()` and `test_quantity_factory_rejects_non_quantity()`) actually correct?**
  _`quantity_factory()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `BaseNode` (e.g. with `ComplianceCheckNode` and `_Fallback`) actually correct?**
  _`BaseNode` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TestPoint` (e.g. with `PerformanceChecker` and `PerformanceCurve`) actually correct?**
  _`TestPoint` has 6 INFERRED edges - model-reasoned connections that need verification._