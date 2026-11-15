# Graph Report - CentrifugalPump  (2026-11-14)

## Corpus Check
- 161 files · ~129,897 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2466 nodes · 4579 edges · 216 communities (147 shown, 69 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 313 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ef15dba0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- GraphScene
- app.py
- binding.py
- WelcomeDialog
- registry.py
- MainWindow
- PerformanceChecker
- UnitField
- TestPoint
- Q_
- SpeedCorrectionNode
- ReportGenerator
- BaseNode
- DesignPoint
- GraphView
- quantity_factory
- units.py
- unit_conversion.py
- PerformanceFitter
- PointNode
- docs/sprints/sprint-03-gui-openable-case.md
- ADR 0001 Establish an automated test harness
- Fluid
- docs/product/audience.md
- Module Reference
- BasePoint
- PerformancePlotNode
- tests/test_compliance.py
- docs/product/use-cases.md
- docs/sprints/sprint-01-test-foundation.md
- QPushButton
- conftest.py
- 2. Findings in detail
- ReportExportNode
- docs/sprints/sprint-02-pin-mvp-physics.md
- docs/sprints/sprint-04-docstrings-doctests.md
- curve_fit.py
- FluidNode
- test_affinity.py
- System Architecture Blueprint — CentrifugalPump
- ReportBundle
- ADR 0007 Remove ACL leak (private-attribute pinning in binding)
- conf.py
- pumpflow/units.py
- ADR 0002 Fix pint NameError in units foundation
- ADR 0003 Correct Python version floor metadata
- ADR 0008 Separate node logic from Qt dialogs
- ADR 0010 Align versioning and declare GUI dependencies
- pumpflow/docs/modules.md
- pumpflow/mathx.py
- UI As-Built Register — pumpflow Workbench
- Tutorial — Running & Testing CentrifugalPump
- theme.py
- Spec-Driven Software Engineering: Adapting the CentrifugalPump Project to the OpenSpec Methodology
- LatexReportGenerator
- test_persistence_roundtrip.py
- test_report_formats.py
- RUN_AND_TEST.md
- CLAUDE.md
- README.md
- PerformanceCurve
- ExploreChartNode
- QLabel
- ARCHITECTURE.md
- Build & Development Guide
- NodeItem
- PortItem
- Dev Journey — your map when it feels like too much
- test_pump_smoke.py
- Removal Map — scaffolding vs. product
- EdgeItem
- AGENTS.md
- MVP use cases
- Node & Banner State Colors
- scene.py
- PumpLab / PumpFlow — Release Notes
- Plan Evaluation: iOS Version
- Plan Evaluation: Web Version
- Centrifugal Pump
- pumpflow theming — editing the color scheme
- UnitPrefs
- Architectural Analysis of the CentrifugalPump Project
- export_cli.py
- Overview & quickstart
- report_latex.py
- LocalizationHelper
- Architecture
- PumpFlow — API 610 Pump Performance Workbench
- Changelog
- Multi-unit handling — design philosophy
- Audience
- Sprint S1 — Test foundation + units spec (8 h)
- Sprint S2 — Pin the MVP physics (8 h)
- Sprint S3 — GUI-openable case + persistence guard (8 h)
- Sprint S4 — Docstrings & doctests (8 h)
- Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)
- .__init__
- PumpLab — Documentation
- RatedPointInputNode
- ADR 0003 — Correct the Python version floor metadata
- ADR 0004 — Refactor `PerformanceCurve`: split plotting from computation
- ADR 0008 — Separate node logic from Qt dialogs
- Architecture Decision Records (ADRs)
- Sprint S0 — Product context & sprint scaffold (8 h)
- Sprint S6 — Repo README + wrap (8 h)
- .to_fluid
- run
- ADR 0002 — Fix the `pint` `NameError` in the units foundation
- ADR 0005 — Consolidate the `Point` hierarchy & remove broken code
- ADR 0006 — Replace `hasattr` duck-typing with an explicit schema
- ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`
- ADR 0009 — Promote `mathx` into the `pump` library
- ADR 0010 — Align versioning & declare GUI dependencies
- reactive_evaluation.md
- hline
- int_spin
- line_edit
- ADR 0004 Refactor PerformanceCurve (split plotting from computation)
- ADR 0005 Consolidate Point hierarchy and remove broken code
- ADR 0006 Replace hasattr duck-typing with explicit schema
- ADR 0009 Promote mathx into pump library
- docs/UI_SPEC.md
- docs/adr/README.md
- docs/ARCHITECTURE.md
- docs/README.md
- docs/RUN_AND_TEST.md
- docs/sprints/README.md
- docs/sprints/sprint-00-product-context.md
- examples/sample_project.pumpflow
- pump/performance_curve.py
- pump/point.py
- pump/utilities/fluid.py
- pump/utilities/unit_conversion.py
- pumpflow/binding.py
- pumpflow/canvas/scene.py
- pumpflow/sample_data.py
- tests/conftest.py
- tests/test_affinity.py
- tests/test_persistence_roundtrip.py
- tests/test_utilities.py
- tests/utilities_test.ipynb
- centrifugal-pump
- pumpflow package (__init__.py)
- pumpflow/app.py
- Boundary: only pumpflow/binding.py may call into pump
- pumpflow/binding.py
- Data-exchange JSON format (unit/rated/points; comma or dot decimals)
- pumpflow/docs/architecture.md
- pumpflow/docs/data_formats.md
- pumpflow/docs/index.md
- pumpflow/docs/user_guide.md
- Immutable typed signals (frozen dataclasses) flowing along canvas links
- pumpflow/numfmt.py
- pumpflow/persistence.py
- Project file format (.pumpflow: nodes/edges/settings; plus meta/view)
- Reactive evaluation loop (topological recompute of node graph)
- pumpflow/README.md
- pumpflow/sample_data.py
- Shared-fluid constraint workaround (pin per-row head/eff onto TestPoint; curve uses single fluid label)
- pumpflow/signals.py
- Units philosophy: store canonical magnitudes; conversions route through quantity_factory; GUI chooses display units
- Sprint 5 — Edition-aware acceptance engine
- Sprint 6 — UC-11 Mechanical run acceptance
- Sprint 7 — UC-08 Compare pumps (twin A vs B)
- Sprint 8 — UC-05 NPSH margin
- Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766)
- Data Formats
- Banner
- NaturalCubicSpline
- .__init__
- 001_masterpiece — Loop Protocol
- .paint
- hline
- .to_speed
- .__getitem__
- .import_data_file
- .__len__
- .__repr__
- checkbox
- export_cli.py
- PerformancePlotNode
- .absolute
- Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)
- TestPointsTableNode
- Data Formats
- line_edit
- SystemCurveNode
- .is_empty
- .density_rel
- ._mark_clean
- UnitPrefs
- Pressures
- correct_curve
- __init__.py
- .__init__
- check_npsh_set
- Data Formats
- .available
- _fmt_value
- test_compliance_gui.py
- test_head_gui.py
- .absolute
- ADR 0002 — Fix the `pint` `NameError` in the units foundation
- SpeedCorrectionNode
- Sprint S4 — Docstrings & doctests (8 h)
- ADR 0006 — Replace `hasattr` duck-typing with an explicit schema
- PumpLab — Documentation
- ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`
- ADR 0009 — Promote `mathx` into the `pump` library
- delta_pint
- upgrade_v1

## God Nodes (most connected - your core abstractions)
1. `BaseNode` - 50 edges
2. `make_node()` - 48 edges
3. `quantity_factory()` - 47 edges
4. `PerformanceChecker` - 40 edges
5. `GraphScene` - 39 edges
6. `PerformanceCurve` - 38 edges
7. `TestPoint` - 36 edges
8. `Water` - 36 edges
9. `BindingError` - 36 edges
10. `MainWindow` - 33 edges

## Surprising Connections (you probably didn't know these)
- `test_checker_limits_match_default_criteria()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_f02_check_summary_lists_rated_rows_only()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_parallel_operation_ok()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_shutoff_not_extrapolated_with_q0_point()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_checker_head_tolerance_band()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_pump_smoke.py → pump/performance_curve.py

## Import Cycles
- 1-file cycle: `pump/__init__.py -> pump/__init__.py`
- 1-file cycle: `pump/utilities/__init__.py -> pump/utilities/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/report_export.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/operating_point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/performance_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/compliance.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/trim.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/fluid.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/rated_point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/correction.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/curve_fit.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/explore_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/markdown_note.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/mechanical_run.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/npsh.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/system_curve.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/test_points.py -> pumpflow/nodes/__init__.py`

## Hyperedges (group relationships)
- **PumpFlow Layered Architecture (UI -> logic -> binding -> library)** — pumpflow_app_module, pumpflow_signals_module, pumpflow_binding_module, pumpflow_persistence_module, pumpflow_units_module, pumpflow_reactive_topological_evaluation, pumpflow_binding_boundary_single_entry [EXTRACTED 1.00]

## Communities (216 total, 69 thin omitted)

### Community 0 - "GraphScene"
Cohesion: 0.11
Nodes (11): _elide(), NodeItem, QGraphicsObject, QRectF, GraphScene, QPointF, Recompute every node in topological order and refresh the canvas., Serialize the canvas as a schema-v2 project document.          Node runtime sett (+3 more)

### Community 1 - "app.py"
Cohesion: 0.10
Nodes (26): canonical_columns(), default_columns(), default_geometry_settings(), _geo_quantity(), geometry_from_settings(), parse_paste_header(), _pint_of(), Q_ (+18 more)

### Community 2 - "binding.py"
Cohesion: 0.12
Nodes (31): assemble_report_data(), check_compliance(), criteria_for(), default_tolerances(), make_design_point(), make_rated_fluid(), Construct the shared ``DesignPoint`` (UI_SPEC §4)., The ``AcceptanceCriteria`` selected by the rated point.      Falls back to the l (+23 more)

### Community 3 - "WelcomeDialog"
Cohesion: 0.14
Nodes (7): diameter_for_duty(), Q_, Impeller diameter that makes ``curve`` pass through the duty ``(q, h)``.      Pa, Impeller trim — UC-07 (sprint 10).  Pins :meth:`pump.PerformanceCurve.to_diamete, test_diameter_for_duty_on_the_curve_is_the_reference(), test_diameter_for_duty_out_of_range_raises(), test_diameter_for_duty_recovers_known_diameter()

### Community 4 - "registry.py"
Cohesion: 0.09
Nodes (29): PumpFlow — API 610 Pump Performance Workbench (Orange-style node canvas).  A thi, PortSpec, nodes.base ==========  The Qt-agnostic logic of a widget node.  A node declares, nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)  Inputs ``FittedMode, nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)  Inputs ``RatedPo, nodes.curve_fit — Curve Fit  (UI_SPEC §5.4)  Input ``CorrectedCurve`` → output `, nodes.explore_plot — Performance Explorer  An *interactive* exploratory chart (p, ``(value - ref) / ref`` as a signed percent string; ``—`` when undefined. (+21 more)

### Community 5 - "MainWindow"
Cohesion: 0.19
Nodes (6): MainWindow, Switch the project's display-unit preset (File-level preference)., Reflect the active ``units.PREFS`` preset in the Units menu check., Flag the session as having unsaved changes.          Appends an asterisk to the, QAction, QMainWindow

### Community 6 - "PerformanceChecker"
Cohesion: 0.13
Nodes (15): PerformanceChecker, Generates a summary table checking if performance values are within limits., A class to check and validate the performance of a system based on a design poin, True when no curve point lies below ``shutoff_extrapolation_q_fraction``, test_acceptable_limits_argument_warns(), test_no_warning_without_acceptable_limits(), API 610 compliance bands — UC-02 (verify pump performance / FAT).  Pins the nume, test_acceptable_limits_exposes_all_bands() (+7 more)

### Community 7 - "UnitField"
Cohesion: 0.07
Nodes (17): The unit combo of a ``ui.PressureField`` (tolerant of its internals)., _unit_combo(), combo(), link_pressure_fields(), PressureField, A unit-aware numeric field: a spinbox + a display-unit combo that     auto-conve, Programmatically switch the display unit (converts the shown value)., A pressure field: ``UnitField("pressure")`` plus a gauge/absolute combo.      Co (+9 more)

### Community 8 - "TestPoint"
Cohesion: 0.13
Nodes (19): Calculates the head difference due to change in fluid velocity.          ``(v_ou, Q_, quantity_factory(), Converts a given quantity to its corresponding standard unit.          Parameter, Converts a given quantity to its standard unit. It is the entry point of     eng, Dynamic viscosity of liquid water at ``temp_c`` (°C) — cP.      Delegates to ``p, Kinematic viscosity of liquid water at ``temp_c`` (°C) — cSt.      Delegates to, water_dynamic_viscosity_cP() (+11 more)

### Community 9 - "Q_"
Cohesion: 0.14
Nodes (17): The default criteria (``api610:12``, no client overlay)., _curve(), Edition-aware acceptance criteria (Sprint 5) — Qt-free.  Covers the TOML-backed, test_checker_limits_match_default_criteria(), test_default_is_api610_12(), test_default_tolerances_match_historical_values(), test_f02_check_summary_lists_rated_rows_only(), test_f02_extrapolated_note_when_no_q0_point() (+9 more)

### Community 10 - "SpeedCorrectionNode"
Cohesion: 0.17
Nodes (18): body_font(), mono_font(), canvas.theme ============  Central palette + metrics for the workbench — a clean, title_font(), _first_available(), init_fonts(), mono_font(), style =====  Global Qt stylesheet — a clean, calm, professional desktop look in (+10 more)

### Community 11 - "ReportGenerator"
Cohesion: 0.09
Nodes (35): check_npsh(), NPSHCriteria, NPSHResult, NPSH margin rule.  Seeded as *not configured*: both limits are ``None``.      At, True when at least one limit is set., Outcome of :func:`check_npsh`.      ``status`` is ``"pass"``, ``"fail"`` or ``"i, Compare NPSHa with NPSHr under an optional margin rule.      The status is ``"in, export_reports() (+27 more)

### Community 12 - "BaseNode"
Cohesion: 0.05
Nodes (59): bisect_root(), NaturalCubicSpline, ndarray, r_squared(), fitting =======  Curve-fitting and root-finding helpers shared by the library an, Return ``(xs, ys)`` of ``n`` evenly spaced samples across the data., Coefficient of determination, R²., Root of ``f`` in ``[lo, hi]`` by bisection.      The interval must bracket a sig (+51 more)

### Community 13 - "DesignPoint"
Cohesion: 0.18
Nodes (4): PortItem, QGraphicsObject, QPointF, QRectF

### Community 14 - "GraphView"
Cohesion: 0.12
Nodes (8): GraphView, QPointF, Capture the current zoom + scene-space center for ``.pumpflow`` files., Restore a zoom + center previously captured by :meth:`view_state`., Apply a multiplicative zoom about the cursor, clamped to the band., Scroll the viewport by a pixel delta (touchpad / plain wheel pan)., Frame every node in the view (zoom extents), clamped to the zoom band., QGraphicsView

### Community 15 - "quantity_factory"
Cohesion: 0.06
Nodes (62): correct_curve(), format_geometry(), _geometry_point(), _has_viscosity(), Q_, Temporary ``pump.TestPoint`` carrying the row's ΔP and the bench geometry., Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):     ``Head =, Head split into its terms, all in metres (tooltips / reports).      Returns ``{" (+54 more)

### Community 16 - "units.py"
Cohesion: 0.13
Nodes (19): atm_in(), convert_display(), _convert_viscosity(), label_for(), _match_unit(), options_for(), parse_unit_header(), pint_str() (+11 more)

### Community 17 - "unit_conversion.py"
Cohesion: 0.10
Nodes (16): _dimensionless(), _kinematic_viscosity(), Create a new PerformanceCurve by assigning a new fluid to all TestPoints., Create a new PerformanceCurve corrected from water to a viscous liquid         (, Float value of a dimensionless quantity (percent aware) or a number., Kinematic viscosity (cSt) of ``fluid``.      Reads ``kinematic_viscosity`` (e.g., Fluid, Returns a detailed string representation of the fluid. (+8 more)

### Community 19 - "PerformanceFitter"
Cohesion: 0.14
Nodes (10): PerformanceFitter, ndarray, Lazily computes the polynomial regression coefficients for head vs. capacity., Lazily computes the polynomial regression coefficients for efficiency vs. capaci, Lazily computes the polynomial regression coefficients for power vs. capacity., Handles polynomial regression for performance metrics (head, efficiency, power),, Lazily computes and returns the capacity values as a NumPy array.          Retur, Lazily computes and returns the head values as a NumPy array.          Returns (+2 more)

### Community 20 - "PointNode"
Cohesion: 0.09
Nodes (7): canvas.node_item ================  The on-canvas representation of one workflow, BaseNode, Return ``{output_port_name: payload}``.  Override me., Return a configured ``QDialog`` (or ``None`` if the node has none)., Helper: clear outputs and show an amber/idle status (UI_SPEC §7)., Plain-JSON view of ``settings`` for ``.pumpflow`` (override if needed)., MarkdownNoteNode

### Community 23 - "Fluid"
Cohesion: 0.13
Nodes (18): Exception, BindingError, make_fluid(), make_system_curve(), Construct a ``pump.Fluid`` (or ``Water``) from a Fluid-node spec (UC-00)., Build a :class:`SystemCurveSpec` from node-level quantities.      ``mode`` is ``, Operating point of a fitted pump curve on a system curve., Human-readable wrapper around library/validation failures (UI_SPEC §7). (+10 more)

### Community 25 - "Module Reference"
Cohesion: 0.06
Nodes (32): `base.BaseNode` + `PortSpec`, `BranchBundle` / `ReportBundle`, `CorrectedCurve`, `EdgeItem` *(QGraphicsPathItem)*, `FittedModel`, `GraphScene` *(QGraphicsScene)*, `GraphView` *(QGraphicsView)*, `MainWindow` (+24 more)

### Community 26 - "BasePoint"
Cohesion: 0.18
Nodes (6): BasePoint, Returns a detailed string representation of the fluid's properties., Represents a system point with physical quantities.      Parameters     --------, Returns a detailed string representation of the fluid's properties., Returns a detailed string with fluid's properties., Returns a detailed string representation of the fluid's properties.

### Community 27 - "PerformancePlotNode"
Cohesion: 0.16
Nodes (18): json_from_signals(), _mag(), _normalize_unit(), _num(), _opt(), persistence ===========  Two on-disk formats (UI_SPEC §6):  - **Data-exchange JS, Export back to the §6.2 shape (exporter mirrors importer)., ``Q_(value, unit)`` or ``None`` (floats ↔ Quantities at the JSON edge). (+10 more)

### Community 31 - "QPushButton"
Cohesion: 0.09
Nodes (25): ABC, _parse_bands(), _parse_quantity(), Q_, acceptance ==========  Edition-aware acceptance criteria (tolerance tables) for, Parse ``"75 m"`` / ``"inf m"`` into a Pint quantity., compare =======  Side-by-side comparison of several fitted :class:`~pump.Perform, constants =========  Physical constants shared by the whole library, as Pint qua (+17 more)

### Community 32 - "conftest.py"
Cohesion: 0.14
Nodes (13): One log line: clock ``time`` ("HH:MM") and ``{channel name: Q_}`` values.      A, RunReading, build_log(), _col_pint(), _default_columns(), _default_rows(), MechanicalRunNode, _next_time() (+5 more)

### Community 33 - "2. Findings in detail"
Cohesion: 0.11
Nodes (19): 2. Findings in detail, 🔴 F-01 — `acceptable_limits` raises instead of degrading, 🔴 F-02 — Head verdict applied at the wrong altitude, 🔴 F-03 — `test_data` builds ragged/crashing columns, 🔴 F-04 — `to_fluid` is stricter and quieter than `to_speed`, 🟠 F-05 — Two acceptance criteria that can disagree at the edge, 🟠 F-06 — Fit degree is unvalidated and inconsistent, 🟠 F-07 — Shutoff head is an unlabeled extrapolation (+11 more)

### Community 35 - "ReportExportNode"
Cohesion: 0.24
Nodes (9): _convert(), _norm(), settings_codec ==============  Qt-free translation between node **runtime settin, Test-points table: runtime ``columns`` (labels) <-> on-disk ``columns`` (Pint)., v1 runtime shape (``unit`` + canonical rows) -> ``columns`` shape., Normalise the compact ``%`` spelling to Pint's ``percent``., Convert ``value`` from ``src`` to ``dst``; untouched when the units agree., _same_unit() (+1 more)

### Community 38 - "curve_fit.py"
Cohesion: 0.09
Nodes (23): migrate(), Path, Raw JSON read (also used for the §6.2 exchange JSON; never migrated)., Upgrade a ``.pumpflow`` document to schema v2 (pure, idempotent).      Returns a, Read a ``.pumpflow`` project file and migrate it to the current schema., read_json(), read_project(), test_upgrade_v1_sets_acceptance_keys() (+15 more)

### Community 41 - "System Architecture Blueprint — CentrifugalPump"
Cohesion: 0.08
Nodes (24): 1.1 The system is two stacked subsystems, 1.2 Primary tech stack, 1.3 Layer responsibilities, 1. Executive system architecture, 2.1 Data flow (happy path), 2.2 System boundaries & integration touchpoints, 2. Component topology (visual map), 3. Core domains & design patterns (+16 more)

### Community 42 - "ReportBundle"
Cohesion: 0.13
Nodes (21): b_parameter(), correction_factors(), Q_, viscosity =========  Viscosity correction of a water-test performance curve (HI, HI 9.6.7 viscosity parameter B (ANSI/HI 9.6.7-2010 Eq. 3, US-unit form).      Th, HI 9.6.7 correction factors ``(C_Q, C_H, C_eta)`` (ANSI/HI 9.6.7-2010 Eq. 4-7)., _b34004a_set(), _g() (+13 more)

### Community 53 - "UI As-Built Register — pumpflow Workbench"
Cohesion: 0.09
Nodes (21): 1. Goal & Scope (As-Built), 2. Reference Workflow (from the notebook), 3. Data Model & Inter‑widget "Signals", 4. Library Binding (mandatory), 5.1 Rated Point Input, 5.2 Test Points Table, 5.3 Speed / Affinity Correction, 5.4 Curve Fit (+13 more)

### Community 54 - "Tutorial — Running & Testing CentrifugalPump"
Cohesion: 0.10
Nodes (21): 1. Prerequisites, 2. Installation, 3. Running the `pump` library, 4. Running the `pumpflow` desktop app, 5. Testing, 6. Troubleshooting, 7. Quick reference, A first end-to-end run (+13 more)

### Community 55 - "theme.py"
Cohesion: 0.31
Nodes (5): canvas.edge_item ================  A bezier link carrying a signal from an outpu, canvas package — reactive node-graph scene/view/items (PySide6)., canvas.port_item ================  A single connection point on a node (an Orang, canvas.scene ============  The reactive node-graph scene.  - holds :class:`NodeI, canvas.view ===========  A pannable / zoomable view over the node graph.  All in

### Community 56 - "Spec-Driven Software Engineering: Adapting the CentrifugalPump Project to the OpenSpec Methodology"
Cohesion: 0.10
Nodes (19): 1.1 Specification-by-Example (SBE) and Behavior-Driven Development (BDD), 1.2 Living Documentation, 1.3 Traceability and Change Proposals, 1. Theoretical Fundamentals of OpenSpec, 2.1 Technical and Strategic Alignment, 2.2 Decision Matrix, 2. Evaluation: Should You Implement This?, 3.1 Step-by-Step "How" Guide (+11 more)

### Community 57 - "LatexReportGenerator"
Cohesion: 0.12
Nodes (17): Figure, NPSHrCurve, plot_npsh(), BytesIO, ndarray, Q_, Least-squares polynomial of NPSHr versus capacity.      Parameters     ---------, NPSHr (metres) at capacity ``q`` from the fitted polynomial. (+9 more)

### Community 58 - "test_persistence_roundtrip.py"
Cohesion: 0.27
Nodes (3): EdgeItem, QPointF, QGraphicsPathItem

### Community 59 - "test_report_formats.py"
Cohesion: 0.19
Nodes (15): npsh3_from_sweep(), npsh_margin(), NPSH3 from a suction sweep at one flow.      The sweep is a series of decreasing, Ratio ``NPSHa / NPSHr`` and margin ``NPSHa - NPSHr``.      Examples     --------, _b34004a_curve(), _hand_npsha(), NPSH margin (UC-05): NPSHa, NPSH3 sweep, NPSHr curve, margin / check, the legacy, test_b34004a_npshr_at_rated_and_ratio() (+7 more)

### Community 60 - "RUN_AND_TEST.md"
Cohesion: 0.18
Nodes (9): 60-second orientation, CentrifugalPump — Documentation, Deeper references (pumpflow UI), Start here, 1 · Data-exchange JSON (UI_SPEC §6.2), 2 · Project file — `.pumpflow` (UI_SPEC §6.1), 3 · Report outputs, Data Formats (+1 more)

### Community 61 - "CLAUDE.md"
Cohesion: 0.13
Nodes (13): Architecture — the `pump` library, Architecture — the `pumpflow` workbench, Common commands, Conventions and gotchas, Domain model: `Fluid` + the `BasePoint` hierarchy, graphify, Identity convention, Key engineering constraint (shared-fluid) (+5 more)

### Community 62 - "README.md"
Cohesion: 0.24
Nodes (6): Sprint index, Sprint template, Sprints, Contents, Guidelines, Use-case worked examples

### Community 63 - "PerformanceCurve"
Cohesion: 0.09
Nodes (20): _fmt_value(), PerformanceCurve, Any, Q_, Table of the rated-point checks (not of every raw test point):         Head and, Generates a report summarizing predicted performance values.                  Re, A container for handling a collection of TestPoint objects that share the same f, Predicts the head for a given flow (capacity) using the stored polynomial. (+12 more)

### Community 64 - "ExploreChartNode"
Cohesion: 0.18
Nodes (13): _blank_rows(), calc_npsha(), _m(), NPSHNode, overrides_to_quantities(), points_from_settings(), Q_, nodes.npsh — NPSH margin  (sprint 8 / UC-05)  Source node.  NPSHr test points (Q (+5 more)

### Community 65 - "QLabel"
Cohesion: 0.07
Nodes (17): QTableWidget, CurveFitNode, OperatingPointNode, Banner, PropertyDialog, QDialog, QWidget, A status / validation chip (UI_SPEC §7). (+9 more)

### Community 66 - "ARCHITECTURE.md"
Cohesion: 0.12
Nodes (16): _band(), diameter_for_rated(), _has_eff(), _limit(), binding =======  The single place where the UI calls **into** the ``pump`` libra, Display row (m³/h, m, kW, %) of one curve point., Impeller-trim a corrected curve or fitted model (``PerformanceCurve.to_diameter`, Diameter at which the curve passes through the rated duty (affinity parabola). (+8 more)

### Community 67 - "Build & Development Guide"
Cohesion: 0.15
Nodes (12): 1. Prerequisites, 2. Environment Setup, 3. Running the Applications, 4. Code Quality & Testing, 5. Building Documentation, 6. Creating a Distributable Package, Build & Development Guide, Formatting (+4 more)

### Community 68 - "NodeItem"
Cohesion: 0.17
Nodes (10): AcceptanceCriteria, _band_for(), deviation(), Tolerances of the first band whose limit is >= ``rated_head``., Tolerance tables for one standard edition, optionally overlaid by a client., ``(minus, plus)`` head tolerance for a rated differential head., ``(minus, plus)`` shut-off head tolerance.          Keyed by the **rated differe, Alias of the module-level :func:`deviation`. (+2 more)

### Community 69 - "PortItem"
Cohesion: 0.19
Nodes (9): Path, Clear the unsaved-changes flag.          Removes the asterisk appended by :meth:, Replace the canvas with *doc* and update session state.          Parameters, Serialise the canvas to the current ``.pumpflow`` file (File > Save).          F, Serialise the canvas to a chosen ``.pumpflow`` path (File > Save As)., Load a ``.pumpflow`` project file into the canvas (File > Open).          Guards, write_json(), Prepend *path* to the persisted recent-files list.      Deduplicates and caps th (+1 more)

### Community 70 - "Dev Journey — your map when it feels like too much"
Cohesion: 0.17
Nodes (12): 2026-10-27, A use case is "in production" when…, Dev Journey — your map when it feels like too much, Latest Work Log, Read this when you're overwhelmed, The next sprints (sequenced for you), The one rule, The second rule — structure by domain, steer by use cases (+4 more)

### Community 71 - "test_pump_smoke.py"
Cohesion: 0.07
Nodes (40): Channel, ChannelResult, MechanicalRunChecker, MechanicalRunLog, MechanicalRunResult, _parse_quantity(), _parse_time(), Q_ (+32 more)

### Community 72 - "Removal Map — scaffolding vs. product"
Cohesion: 0.18
Nodes (11): Bottom line, Lower-confidence candidate (verify before acting), Removal Map — scaffolding vs. product, Routine hygiene — clear the regenerable artifacts (not a removal), The principle, Tier 1 — Remove: vendored dev scaffolding (no longer referenced), Tier 2 — Consolidate: divergent duplicate → one gallery example, Tier 3 — Decide: dev-time smoke scaffolding (+3 more)

### Community 73 - "EdgeItem"
Cohesion: 0.24
Nodes (5): _btn(), _pick_dir(), _pick_file(), ReportExportNode, QPushButton

### Community 74 - "AGENTS.md"
Cohesion: 0.20
Nodes (9): Commands (Match Repo Config), Fast Orientation, graphify, Hard Boundary, Persistence Guard, Repo Noise, Reports / Localization, Testing Gotchas (+1 more)

### Community 75 - "MVP use cases"
Cohesion: 0.14
Nodes (14): Deferred to v1.1 (library gaps — recorded, not built in this plan), MVP use cases, Out of scope, Priority summary, UC-00 — Work in the engineer's own measurement units ✅, UC-02 — Verify pump performance (FAT) ✅, UC-03 / UC-04 — System curve and operating point ✅, UC-05 — Check NPSH margin ✅ (+6 more)

### Community 76 - "Node & Banner State Colors"
Cohesion: 0.20
Nodes (9): Banners (`#Banner`), Color Palette, Compliance Verdicts (`#VerdictBanner`), Improving Contrast, Node & Banner State Colors, Node Canvas Item Anatomy, Node Property Dialog Anatomy, Primary Colors (+1 more)

### Community 77 - "scene.py"
Cohesion: 0.07
Nodes (17): Access an individual TestPoint by index.          Parameters         ----------, Specialized version of the BasePoint class for handling test or operational data, Calculates the head generated due to pressure difference.          Returns, Calculates the fluid velocity at the pump inlet.          Returns         ------, Calculates the fluid velocity at the pump outlet.          Returns         -----, Calculates the head difference due to elevation.          ``outlet_elevation - i, Computes the total dynamic head (TDH) from its components.          The TDH is t, The total dynamic head of the point.          Returns a cached `_head` value if (+9 more)

### Community 78 - "PumpLab / PumpFlow — Release Notes"
Cohesion: 0.20
Nodes (9): Breaking Changes / Migration Guide, Bug Fixes, Changelog, Improvements, Key Highlights, New Features, Notes for library maintainers, PumpLab / PumpFlow — Release Notes (+1 more)

### Community 79 - "Plan Evaluation: iOS Version"
Cohesion: 0.20
Nodes (9): 1. Application Rendering, 2. Output Rendering (Reports), 3. Workflow Rendering (Canvas Export), 4. Component Catalog Rendering, Conclusion, Executive Summary, Plan Evaluation: iOS Version, Proposed Architecture: A Complete Rewrite (+1 more)

### Community 80 - "Plan Evaluation: Web Version"
Cohesion: 0.20
Nodes (9): 1. Application Rendering, 2. Output Rendering (Reports), 3. Workflow Rendering (Canvas Export), 4. Component Catalog Rendering, Conclusion, Executive Summary, Plan Evaluation: Web Version, Proposed Architecture: Client-Server (+1 more)

### Community 81 - "Centrifugal Pump"
Cohesion: 0.20
Nodes (10): Building distributions, Centrifugal Pump, Developers (conda/mamba), Documentation, Installation & packaging, Quickstart, Regular users, Roadmap (+2 more)

### Community 82 - "pumpflow theming — editing the color scheme"
Cohesion: 0.22
Nodes (8): Adding a color for a new signal/port type, Metrics (not colors, but in the same file), pumpflow theming — editing the color scheme, Seeing your changes, ⚠️ The shared accent color lives in BOTH files, The two sources of color, What you see on screen → what to edit, Worked example — switch the accent from blue to teal

### Community 83 - "UnitPrefs"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 1 — Library quantity spine, Tests

### Community 84 - "Architectural Analysis of the CentrifugalPump Project"
Cohesion: 0.22
Nodes (8): Architectural Analysis of the CentrifugalPump Project, Conclusion and Recommendation, Evaluating the Path Forward: Web and iOS, Introduction: A Tale of Two Halves, The Cornerstone: A Clean Separation of Concerns, The Current State: A Desktop-First, Expert-Oriented Paradigm, The iOS Version: Impractical and Not Recommended, The Web Version: Feasible but Demanding

### Community 85 - "export_cli.py"
Cohesion: 0.15
Nodes (11): Key decisions (2026-11-14), Levers / approach, Risks, The problem, Why 001_masterpiece exists, 001_masterpiece — Loop Protocol, 001_masterpiece — Pint end to end, every use case, FAT-grade acceptance, Changelog (+3 more)

### Community 86 - "Overview & quickstart"
Cohesion: 0.29
Nodes (6): A 30-second FAT computation, How the pieces fit, Install, Overview & quickstart, Run the tests, The visual workbench

### Community 87 - "report_latex.py"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 11 — UC-03 System curve + UC-04 Operating point, Tests

### Community 88 - "LocalizationHelper"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 12 — UC-01 Pump selection, Tests

### Community 89 - "Architecture"
Cohesion: 0.29
Nodes (7): 1. The reactive data-flow model, 2. The evaluation loop, 3. Interactive edge creation, 4. The two-pump (A/B) topology, 5. Persistence boundaries, Architecture, Signal types and the ports that carry them

### Community 90 - "PumpFlow — API 610 Pump Performance Workbench"
Cohesion: 0.29
Nodes (6): Canvas controls, `.docx` export, Install & run, PumpFlow — API 610 Pump Performance Workbench, Two engineering notes, What maps to the spec

### Community 91 - "Changelog"
Cohesion: 0.33
Nodes (5): [0.1.0] — initial release, Added, Changed, Changelog, [Unreleased]

### Community 92 - "Multi-unit handling — design philosophy"
Cohesion: 0.33
Nodes (5): Back-compatibility, Extending it, How it is wired, Multi-unit handling — design philosophy, The invariants

### Community 93 - "Audience"
Cohesion: 0.33
Nodes (6): Audience, Primary — Performance test / FAT engineer, Repo-vs-spec discrepancy, Roles explicitly out of scope, Secondary — Application / selection engineer *(pending owner sign-off)*, Tertiary — Student / learner *(pending owner sign-off)*

### Community 94 - "Sprint S1 — Test foundation + units spec (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S1 — Test foundation + units spec (8 h), Tasks (≈ 8 h)

### Community 95 - "Sprint S2 — Pin the MVP physics (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S2 — Pin the MVP physics (8 h), Tasks (≈ 8 h)

### Community 96 - "Sprint S3 — GUI-openable case + persistence guard (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S3 — GUI-openable case + persistence guard (8 h), Tasks (≈ 8 h)

### Community 97 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.09
Nodes (22): npsh_available(), NPSH available at the pump suction, in metres.      ``NPSHa = (p_s,abs - p_v) /, Pressure, Any, Q_, Difference of two pressures (reference-free), in the units of ``self``., Serialise to ``{"value", "unit", "ref", "atm": {"value", "unit"}}``.          Ex, Rebuild from :meth:`to_json` output (``ref`` defaults to gauge, ``atm`` (+14 more)

### Community 98 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.08
Nodes (17): _kinematic_viscosity(), Q_, Liquid water at a given temperature.      Density is computed from a 4th-order p, Dynamic viscosity of liquid water, in cP.          Andrade-style exponential fit, Kinematic viscosity of liquid water (dynamic viscosity / density), in cSt., Saturation (vapour) pressure of water, absolute, in kPa.          Source: IAPWS-, Initializes a Fluid object with converted physical properties.          Paramete, Water (+9 more)

### Community 99 - ".__init__"
Cohesion: 0.10
Nodes (15): DesignPoint, Q_, Specific energy is the energy per unit mass of fluid.         It is calculated a, The mechanical power transferred to the liquid as it passes through the pump,, Calculates the outlet pressure based on inlet pressure and various heads., Calculates the head difference due to elevation.          Returns         ------, Calculates the fluid velocity at the pump inlet.          Returns         ------, Calculates the fluid velocity at the pump outlet.          Returns         ----- (+7 more)

### Community 100 - "PumpLab — Documentation"
Cohesion: 0.12
Nodes (16): _client_overlays(), ``[(client, label), ...]`` for every shipped client overlay., Load an edition, optionally merged with a client overlay.          The overlay r, ``{key: (edition_table, standard_title)}`` for every shipped edition., ``{client: overlay_table}`` for every shipped client overlay., _read_toml(), _standards(), test_clients_lists_n553() (+8 more)

### Community 101 - "RatedPointInputNode"
Cohesion: 0.07
Nodes (33): available_clients(), available_standards(), head_from_pressures(), Head in metres from a pressure pair and a constant density (Point node)., ``[(key, label)]`` of the editions the library offers., ``[(client, label)]`` of the client overlays the library offers., Density of water at ``temp_c`` (°C) via ``pump.Water`` — kg/m³ (UC-00)., water_density_kgm3() (+25 more)

### Community 102 - "ADR 0003 — Correct the Python version floor metadata"
Cohesion: 0.40
Nodes (5): ADR 0003 — Correct the Python version floor metadata, Alternative considered, Consequences, Context, Decision

### Community 103 - "ADR 0004 — Refactor `PerformanceCurve`: split plotting from computation"
Cohesion: 0.40
Nodes (5): Acceptance, ADR 0004 — Refactor `PerformanceCurve`: split plotting from computation, Consequences, Context, Decision

### Community 104 - "ADR 0008 — Separate node logic from Qt dialogs"
Cohesion: 0.40
Nodes (5): Acceptance, ADR 0008 — Separate node logic from Qt dialogs, Consequences, Context, Decision

### Community 105 - "Architecture Decision Records (ADRs)"
Cohesion: 0.40
Nodes (5): Architecture Decision Records (ADRs), Status legend, Suggested sequencing, Tracking index — ordered by criticality, What is an ADR?

### Community 106 - "Sprint S0 — Product context & sprint scaffold (8 h)"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S0 — Product context & sprint scaffold (8 h), Tasks (≈ 8 h)

### Community 107 - "Sprint S6 — Repo README + wrap (8 h)"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S6 — Repo README + wrap (8 h), Tasks (≈ 8 h)

### Community 108 - ".to_fluid"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 14 — Masterpiece polish: report, CI, docs, Tests

### Community 109 - "run"
Cohesion: 0.10
Nodes (27): build_report_png(), fit_model(), Polynomial coeffs (primary) + natural cubic splines (secondary)., Reuse the library's matplotlib plot for the report image (BytesIO PNG)., _bundle_json(), _mag(), nodes.report_export — Report Export  (UI_SPEC §5.7)  Inputs: the shared ``RatedP, Float magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``). (+19 more)

### Community 111 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.15
Nodes (7): Smoke / regression tests for the ``pump`` engineering library.  These are intent, test_checker_head_tolerance_band(), test_checker_shutoff_tolerance_tier(), test_mixed_fluid_curve_is_rejected(), test_quantity_factory_canonicalizes_capacity(), test_quantity_factory_rejects_non_quantity(), test_report_summary_keys()

### Community 112 - "ADR 0005 — Consolidate the `Point` hierarchy & remove broken code"
Cohesion: 0.50
Nodes (4): ADR 0005 — Consolidate the `Point` hierarchy & remove broken code, Consequences, Context, Decision

### Community 113 - "ADR 0006 — Replace `hasattr` duck-typing with an explicit schema"
Cohesion: 0.33
Nodes (5): design_point(), Shared pytest fixtures for the ``pump`` library suite.  These were originally in, Cold water at ~997 kg/m³ — the reference fluid for the suite., Rated/design point matching the curve's rated region (833 m³/h, 73 m)., water()

### Community 114 - "ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`"
Cohesion: 0.20
Nodes (11): MechanicalRunCriteria, plot_mechanical_run(), BytesIO, Acceptance criteria of a mechanical running test.      Attributes     ----------, Trend plot as a PNG ``BytesIO``: one subplot per role group present,     role li, check_mechanical_run(), Check a mechanical-run log against the acceptance criteria.      The criteria co, Status verdict; provisional when the limits are not verified. (+3 more)

### Community 115 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.23
Nodes (10): _d(), app ===  The PumpFlow main window: a node toolbox, the reactive canvas, the menu, run(), Run PumpFlow:  python -m pumpflow, parse_decimal(), Parse a number that may use ``,`` or ``.`` as the decimal separator.      Heuris, rated_from_json(), Build a :class:`RatedPoint` from a §6.2 document (comma-decimals ok).      The a (+2 more)

### Community 116 - "ADR 0010 — Align versioning & declare GUI dependencies"
Cohesion: 0.50
Nodes (4): ADR 0010 — Align versioning & declare GUI dependencies, Consequences, Context, Decision

### Community 118 - "hline"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2, Tests

### Community 119 - "int_spin"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 3 — Unit choice on every GUI numeric field, Tests

### Community 120 - "line_edit"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 4 — Complete head (pressure + velocity + elevation), Tests

### Community 166 - "Sprint 5 — Edition-aware acceptance engine"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 5 — Edition-aware acceptance engine, Tests

### Community 167 - "Sprint 6 — UC-11 Mechanical run acceptance"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 6 — UC-11 Mechanical run acceptance, Tests

### Community 168 - "Sprint 7 — UC-08 Compare pumps (twin A vs B)"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 7 — UC-08 Compare pumps (twin A vs B), Tests

### Community 169 - "Sprint 8 — UC-05 NPSH margin"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 8 — UC-05 NPSH margin, Tests

### Community 170 - "Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766)"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 9 — Viscosity correction (HI 9.6.7 / ISO TR 17766), Tests

### Community 171 - "Data Formats"
Cohesion: 0.30
Nodes (10): _col(), _head(), _header(), Qt (offscreen) tests: per-column units on the Test Points table., _select(), _setup(), test_capacity_roundtrip_restores_values_and_head(), test_paste_with_headers_sets_units() (+2 more)

### Community 172 - "Banner"
Cohesion: 0.20
Nodes (5): Guard destructive actions with a Save / Discard / Cancel prompt.          Presen, Create a blank canvas (File > New).          Prompts to save unsaved changes bef, Intercept the window close event to guard unsaved work.          Parameters, Display the start-screen dialog and act on the user's choice.          Called on, Frame the whole pipeline (zoom extents).

### Community 173 - "NaturalCubicSpline"
Cohesion: 0.20
Nodes (8): _disk_unit(), _fmt(), _q_enc(), The unit string written to disk for a display label.      Compact Pint spelling, Optional ``[lo, hi]`` axis limits with a runtime unit label., Runtime ``{"value", "unit": label}`` -> on-disk ``{"value", "unit": pint}``., Compact (``~C``) Pint spelling, as produced by ``pump.quantity_io.to_json``., YLimDisp

### Community 174 - ".__init__"
Cohesion: 0.13
Nodes (14): load_recent(), Path, QDialog, QFrame, QWidget, welcome =======  Start-screen dialog shown on application launch.  Presents Rece, Splash / start-screen modal shown over the main window at launch.      The calle, Build the left column listing the most recently opened projects.          Notes (+6 more)

### Community 175 - "001_masterpiece — Loop Protocol"
Cohesion: 0.13
Nodes (12): Generates a report from predefined templates using the `python-docx` library., Retrieve the appropriate template file based on the selected language., Generates a report from a predefined template.          Parameters         -----, Add introductory section to the document.                  Parameters         --, Add design point section to the document.                  Parameters         --, Add equipment description section to the document.                  Parameters, Add test data section to the document.                  Parameters         -----, Add charts to the document.                  Parameters         ---------- (+4 more)

### Community 176 - ".paint"
Cohesion: 0.27
Nodes (8): _label_or_canonical(), NPSHTable, _pint(), _q_dec(), Pint string of a display label (a bare Pint string is accepted too)., ``(label, converted?)`` for a stored unit: its label, else canonical., On-disk ``{"value", "unit"}`` -> runtime ``{"value", "unit": label}``., NPSH-node settings: per-column units of the NPSHr table + the margin override.

### Community 177 - "hline"
Cohesion: 0.22
Nodes (4): Disp, OptDisp, Value with a runtime display label: ``key`` + ``unit_key`` <-> quantity., Optional :class:`Disp`: an unset (``None``) value is **omitted** on disk.      T

### Community 178 - ".to_speed"
Cohesion: 0.50
Nodes (3): Shared rated point/fluid + one entry per pump TAG, ready to serialize., Acceptance reflects ALL pumps (UI_SPEC §2 / §9)., ReportBundle

### Community 179 - ".__getitem__"
Cohesion: 0.12
Nodes (11): port_color(), _append_param(), ComplianceCheckNode, _Fallback, QTableWidget, Stand-in rated point for the tolerance dialog before a RatedPoint is wired., _append(), _append() (+3 more)

### Community 180 - ".import_data_file"
Cohesion: 0.32
Nodes (3): _mag_or(), Wire a Pump B branch to the same Rated Point + Report (UI_SPEC §2 A/B)., Magnitude of an optional Quantity in ``unit``, or ``default`` when ``None``.

### Community 181 - ".__len__"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 10 — UC-07 Impeller trim, Tests

### Community 182 - ".__repr__"
Cohesion: 0.06
Nodes (59): make_node(), decode(), encode(), Runtime settings -> v2 on-disk settings (new dict; input untouched)., v2 on-disk settings -> runtime settings (new dict; input untouched)., _b34004a_settings(), _node(), Qt (offscreen) tests: Mechanical Run node, codec round-trip, report section (spr (+51 more)

### Community 183 - "checkbox"
Cohesion: 0.13
Nodes (5): Qt-free tests for the multi-unit spine: UNIT_OPTIONS, header parsing, codec., test_codec_decode_unlabelled_columns_go_canonical(), test_codec_roundtrip_test_points_columns(), test_test_points_us_columns_equal_si_columns(), _tp_runtime()

### Community 184 - "export_cli.py"
Cohesion: 0.32
Nodes (7): build_scene(), main(), Headless report export: ``.pumpflow`` project → Word / LaTeX / PDF.  Usage::, Load ``project`` into an evaluated :class:`GraphScene` (offscreen Qt)., ``(rated, branches, settings)`` from the project's Report Export node., report_inputs(), test_b34004_cli_exports()

### Community 185 - "PerformancePlotNode"
Cohesion: 0.28
Nodes (3): PerformancePlotNode, BytesIO, Y-limits converted from their display unit to canonical m / kW / %.

### Community 186 - ".absolute"
Cohesion: 0.14
Nodes (17): _fmt(), latex_escape(), LatexReportGenerator, Path, Escape LaTeX special characters in ``text`` (converted with ``str``)., Same number formatting as the docx report (``0.02f~P`` for quantities)., Write the FAT report as a LaTeX source and/or a compiled PDF.      Parameters, Write ``output_file`` (``.tex``) plus a ``<stem>_figs/`` folder. (+9 more)

### Community 187 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h), Tasks (≈ 8 h)

### Community 188 - "TestPointsTableNode"
Cohesion: 0.16
Nodes (8): _axis_scale(), ExploreChartNode, _mag(), Pin every left axis to the widest one so the plot frames (and the         shared, A capacity field (any capacity unit) + a table of the values each         fitted, Magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``)., A vertical guide + value label that follows the cursor across panes., ``(scale, display_unit)`` mapping canonical axis values to the preset's     disp

### Community 189 - "Data Formats"
Cohesion: 0.09
Nodes (30): comparison_sentence(), comparison_table(), find_latex_engine(), LaTeX (``.tex``) and PDF report generation.  Consumes the **same** ``report_data, Return the command used to build a PDF, or ``None`` when no TeX is found., mechanical_run_duration_sentence(), mechanical_run_notes(), mechanical_run_table() (+22 more)

### Community 190 - "line_edit"
Cohesion: 0.32
Nodes (7): from_json(), Any, Q_, quantity_io ===========  One serialisation path for Pint quantities: a ``{"value, Serialise a quantity to a JSON-ready ``{"value", "unit"}`` dict.      Parameters, Rebuild a quantity from :func:`to_json` output.      Parameters     ----------, to_json()

### Community 192 - ".is_empty"
Cohesion: 0.17
Nodes (10): LocalizationHelper, _parse_po(), ``Viscosity correction (HI 9.6.7): B = ..., C_Q = ..., C_H = ..., C_η = ...``., Minimal ``.po`` reader: ``{msgid: msgstr}`` for non-empty translations.      Han, Handles translation and localization using gettext.      Parameters     --------, Sets up gettext for localization.          Returns         -------         Calla, viscosity_sentence(), test_parse_po_multiline() (+2 more)

### Community 193 - ".density_rel"
Cohesion: 0.11
Nodes (25): compare_curves(), ComparisonRow, ComparisonTable, plot_comparison(), Q_, Relative delta ``(value - ref) / ref`` (NaN when the reference is zero)., Compare fitted curves at the given capacities.      Parameters     ----------, Overlay head, power and efficiency of several curves (three stacked panels). (+17 more)

### Community 194 - "._mark_clean"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 13 — UC-10 Educational mode + a worked notebook per use case, Tests

### Community 195 - "UnitPrefs"
Cohesion: 0.25
Nodes (4): canonical_unit(), The library's standard display label for a dimension (first option)., Holds the active project-level unit preset (SI / US / custom).      ``default_un, UnitPrefs

### Community 196 - "Pressures"
Cohesion: 0.38
Nodes (3): _atm(), Pressures, Pressures sharing one runtime unit label + g/a reference -> ``{value, unit, ref}

### Community 197 - "correct_curve"
Cohesion: 0.22
Nodes (8): 1. Findings index, 3. Next-generation options, 4. Suggested first sprint (if Option A is accepted), Code Review — Toward the Next-Generation Tool, Option A — Harden the core (recommended first), Option B — Headless-first FAT pipeline (`pump-cli`), Option C — Physics expansion (parallel track), Option D — Web workbench

### Community 199 - ".__init__"
Cohesion: 0.33
Nodes (3): Initializes the PerformanceChecker with a design point and performance curve., Determines the shutoff head tolerance (plus side) from the rated         differe, Computes the acceptable limits for head, shutoff head, and breaking power.

### Community 200 - "check_npsh_set"
Cohesion: 0.33
Nodes (6): check_npsh_set(), criteria_label(), Display label: edition label, plus `` + <client label>`` for an overlay., Display label for an edition key (+ optional client overlay)., Judge a pump's NPSH margin: NPSHa against the NPSHr curve at rated Q.      The c, standard_label()

### Community 202 - ".available"
Cohesion: 0.40
Nodes (4): _edition_sort_key(), ``[(key, label), ...]`` for every shipped edition, sorted., test_available_editions(), test_shipped_npsh_criteria_are_not_configured()

### Community 203 - "_fmt_value"
Cohesion: 0.13
Nodes (17): Return the canonical single-pump ``.pumpflow`` document (Qt-free, schema v2)., sample_project_doc(), b34004_scene(), _build_scene(), ``.pumpflow`` persistence guard — UC-02 / UC-09 (the workbench demo case).  Two, Open every node's property dialog: on the B-34004 project (branch B has     no f, Sprint 10: diameter that puts B-34004A on its rated point lies inside the     da, A template row with no N / P / ΔP must be rejected by validation; before     the (+9 more)

### Community 204 - "test_compliance_gui.py"
Cohesion: 0.29
Nodes (5): Qt (offscreen) test: criteria-aware compliance on the B-34004A reference project, _results(), scene(), test_project_evaluates_with_criteria_metadata(), test_reset_restores_criteria_defaults()

### Community 205 - "test_head_gui.py"
Cohesion: 0.40
Nodes (4): _parse_quantity(), Build from a TOML ``npsh`` table (missing limits stay ``None``)., Parse ``"1 m"`` into a Pint quantity., test_criteria_from_table()

### Community 206 - ".absolute"
Cohesion: 0.50
Nodes (4): ADR 0001 — Establish an automated test harness, Consequences, Context, Decision

### Community 207 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.50
Nodes (4): ADR 0002 — Fix the `pint` `NameError` in the units foundation, Consequences, Context, Decision

### Community 209 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S4 — Docstrings & doctests (8 h), Tasks (≈ 8 h)

### Community 210 - "ADR 0006 — Replace `hasattr` duck-typing with an explicit schema"
Cohesion: 0.50
Nodes (4): ADR 0006 — Replace `hasattr` duck-typing with an explicit schema, Consequences, Context, Decision

### Community 211 - "PumpLab — Documentation"
Cohesion: 0.33
Nodes (6): Capabilities at a glance, Documentation map, Project layout, PumpLab — Documentation, Quick start, The seven widgets

### Community 212 - "ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`"
Cohesion: 0.50
Nodes (4): ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`, Consequences, Context, Decision

### Community 213 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.50
Nodes (4): ADR 0009 — Promote `mathx` into the `pump` library, Consequences, Context, Decision

### Community 214 - "delta_pint"
Cohesion: 0.50
Nodes (4): overrides_to_quantities(), Runtime override dicts (display labels) -> Quantities for the binding., delta_pint(), Pint unit of a *difference* in ``dimension`` shown in ``label``.      Temperatur

## Knowledge Gaps
- **488 isolated node(s):** `centrifugal-pump`, `Fast Orientation`, `Commands (Match Repo Config)`, `Testing Gotchas`, `Hard Boundary` (+483 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **69 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `quantity_factory()` connect `TestPoint` to `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `.__init__`, `BaseNode`, `scene.py`, `ADR 0002 — Fix the `pint` `NameError` in the units foundation`, `units.py`, `unit_conversion.py`, `BasePoint`, `QPushButton`, `PerformanceCurve`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `PerformanceChecker` connect `PerformanceChecker` to `.density_rel`, `binding.py`, `.__init__`, `NodeItem`, `.__init__`, `Q_`, `scene.py`, `ADR 0002 — Fix the `pint` `NameError` in the units foundation`, `QPushButton`, `PerformanceCurve`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `make_node()` connect `.__repr__` to `registry.py`, `MainWindow`, `curve_fit.py`, `_fmt_value`, `test_compliance_gui.py`, `Data Formats`, `quantity_factory`, `ADR 0009 — Promote `mathx` into the `pump` library`, `PointNode`, `export_cli.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `BaseNode` (e.g. with `ComplianceCheckNode` and `_Fallback`) actually correct?**
  _`BaseNode` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `make_node()` (e.g. with `.__init__()` and `build_scene()`) actually correct?**
  _`make_node()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `quantity_factory()` (e.g. with `test_quantity_factory_canonicalizes_capacity()` and `test_quantity_factory_rejects_non_quantity()`) actually correct?**
  _`quantity_factory()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `PerformanceChecker` (e.g. with `AcceptanceCriteria` and `DesignPoint`) actually correct?**
  _`PerformanceChecker` has 28 INFERRED edges - model-reasoned connections that need verification._