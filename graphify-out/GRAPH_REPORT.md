# Graph Report - CentrifugalPump  (2026-11-20)

## Corpus Check
- 311 files · ~248,120 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4151 nodes · 8379 edges · 294 communities (214 shown, 80 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 418 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `94fd02d5`
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
- Pressures
- .absolute
- ADR 0002 — Fix the `pint` `NameError` in the units foundation
- parse_standard_text
- Sprint S4 — Docstrings & doctests (8 h)
- ADR 0006 — Replace `hasattr` duck-typing with an explicit schema
- PumpLab — Documentation
- ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`
- ADR 0009 — Promote `mathx` into the `pump` library
- delta_pint
- upgrade_v1
- ._load_project
- test_head_gui.py
- SelectionCriteria
- PumpLab — Documentation
- PropertyDialog
- Banner
- YLimDisp
- README.md
- UnitColumnHeader
- _bundle_json
- test_notebooks.py
- RunLog
- Affinity laws
- SelectionCriteria
- SystemCurveNode
- Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)
- 001_masterpiece — Loop Protocol
- NPSHNode
- ADR 0009 — Promote `mathx` into the `pump` library
- Data Formats
- Banner
- .deviation
- .compute
- YLimDisp
- CentrifugalPump — Documentation
- _bundle_json
- TestRow
- QSettings
- Disp
- Acceptance tolerances (data-driven)
- .verdict
- .import_data_file
- .absolute
- Pressures
- _disk_unit
- _pint
- Sprint S1 — Test foundation + units spec (8 h)
- .showEvent
- 001_masterpiece — Loop Protocol
- Sprint S0 — Product context & sprint scaffold (8 h)
- export_pumpcurve
- .from_table
- Sprint S6 — Repo README + wrap (8 h)
- ADR 0012 — One performance-verdict engine, no silent passes
- SelectionResult
- Banner
- ADR 0002 — Fix the `pint` `NameError` in the units foundation
- .components_available
- .is_empty
- package.json
- Audience
- UnitColumnHeader
- .from_table
- available_clients
- available_standards
- guards.test.ts
- eslint-plugin-react-hooks
- jsdom
- _vibration_keys
- @types/react
- SelectionCriteria
- Pressures
- vite
- @vitejs/plugin-react
- render
- RatedPoint
- sw-template.js
- ADR 0011 — Schema v2: value + unit persistence
- _default_columns
- welcome.py
- .compute
- .compute
- .create_dialog
- .serialize_settings
- .set_badge
- hline

## God Nodes (most connected - your core abstractions)
1. `make_node()` - 94 edges
2. `BaseNode` - 62 edges
3. `Q` - 58 edges
4. `GraphScene` - 52 edges
5. `PerformanceCurve` - 48 edges
6. `TestPoint` - 46 edges
7. `quantity_factory()` - 46 edges
8. `PerformanceChecker` - 45 edges
9. `RatedPoint` - 45 edges
10. `Graph` - 43 edges

## Surprising Connections (you probably didn't know these)
- `test_checker_limits_match_default_criteria()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_no_warning_without_acceptable_limits()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_parallel_operation_ok()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_acceptance.py → pump/performance_curve.py
- `test_pressure_absolute_to_gauge()` --calls--> `Pressure`  [INFERRED]
  tests/test_quantity_spine.py → pump/utilities/pressure.py
- `test_pressure_difference_is_reference_free()` --calls--> `Pressure`  [INFERRED]
  tests/test_quantity_spine.py → pump/utilities/pressure.py

## Import Cycles
- 1-file cycle: `pump/__init__.py -> pump/__init__.py`
- 1-file cycle: `pump/utilities/__init__.py -> pump/utilities/__init__.py`

## Communities (294 total, 80 thin omitted)

### Community 0 - "GraphScene"
Cohesion: 0.20
Nodes (7): NodeItem, QGraphicsObject, QPointF, QRectF, A filled dot carrying a glyph (✓ ! ✗); idle is a hollow ring., Draw a rounded verdict pill at ``x`` (or centred); return its right edge., Zoomed out: the body shows only the verdict (or a large state glyph).

### Community 1 - "app.py"
Cohesion: 0.09
Nodes (41): uplot, uplot, Chart(), ChartData, ChartMark, ChartProps, ChartSeries, cssVar() (+33 more)

### Community 2 - "binding.py"
Cohesion: 0.16
Nodes (25): check_compliance(), criteria_for(), default_tolerances(), The ``AcceptanceCriteria`` selected by the rated point.      Falls back to the l, Criteria-default tolerances exposed as editable fields (UI_SPEC §5.6).      Both, Evaluate API 610 deviations & verdict.      A thin adapter: the verdict is :func, make_design_point(), Construct the shared ``DesignPoint`` (UI_SPEC §4). (+17 more)

### Community 3 - "WelcomeDialog"
Cohesion: 0.14
Nodes (27): The default criteria (``api610:12``, no client overlay)., MechanicalRunChecker, Check a :class:`MechanicalRunLog` against :class:`MechanicalRunCriteria`., test_default_is_api610_12(), test_default_tolerances_match_table_16(), test_shutoff_tiers_keyed_by_rated_head(), test_tolerance_accepts_other_length_units(), b34004a() (+19 more)

### Community 4 - "registry.py"
Cohesion: 0.05
Nodes (41): canvas.scene ============  The reactive node-graph scene.  - holds :class:`NodeI, Edge, evaluate_in_order(), Graph, engine ======  The Qt-free graph engine.  - pure algorithms shared by every fron, Create a node of ``kind`` (via the registry) and append it., Remove a node and every edge touching it (unknown id is ignored)., Wire an output port to an input port, like ``PortItem.can_accept``.          Rai (+33 more)

### Community 5 - "MainWindow"
Cohesion: 0.08
Nodes (22): _d(), MainWindow, Path, Switch the project's display-unit preset (File-level preference)., Reflect the active ``units.PREFS`` preset in the Units menu check., Flag the session as having unsaved changes.          Appends an asterisk to the, Clear the unsaved-changes flag.          Removes the asterisk appended by :meth:, Guard destructive actions with a Save / Discard / Cancel prompt.          Presen (+14 more)

### Community 6 - "PerformanceChecker"
Cohesion: 0.06
Nodes (29): PerformanceChecker, ``(minus, plus)`` shut-off tolerance: criteria band or user override., Computes the acceptable limits for head, shutoff head, and breaking power., True when no curve point lies below ``shutoff_extrapolation_q_fraction``, Generates a summary table checking if performance values are within limits., A class to check and validate the performance of a system based on a design poin, Initializes the PerformanceChecker with a design point and performance curve., Determines the shutoff head tolerance (plus side) from the rated         differe (+21 more)

### Community 7 - "UnitField"
Cohesion: 0.08
Nodes (15): The unit combo of a ``ui.PressureField`` (tolerant of its internals)., _unit_combo(), combo(), link_pressure_fields(), PressureField, A unit-aware numeric field: a spinbox + a display-unit combo that     auto-conve, Programmatically switch the display unit (converts the shown value)., A pressure field: ``UnitField("pressure")`` plus a gauge/absolute combo.      Co (+7 more)

### Community 8 - "TestPoint"
Cohesion: 0.07
Nodes (31): Catalogue, CatalogueEntry, entry_to_dict(), _has_eff(), load_entry(), Path, One pump curve of the catalogue.      Attributes     ----------     name : str, True when every point of the curve carries an efficiency. (+23 more)

### Community 9 - "Q_"
Cohesion: 0.09
Nodes (28): check_npsh(), NPSHCriteria, NPSHResult, NPSH margin rule.  Seeded as *not configured*: both limits are ``None``.      At, True when at least one margin limit (ratio or margin) is set., Outcome of :func:`check_npsh`.      ``status`` is ``"pass"``, ``"fail"`` or ``"i, Compare NPSHa with NPSHr under an optional margin rule.      The status is ``"in, check_mechanical_run() (+20 more)

### Community 10 - "SpeedCorrectionNode"
Cohesion: 0.18
Nodes (4): PortItem, QGraphicsObject, QPointF, QRectF

### Community 11 - "ReportGenerator"
Cohesion: 0.09
Nodes (40): export_reports(), Write the report in every requested format.      Returns ``(paths, errors)``: ``, _mechanical_run_entry(), _mr_only_data(), _npsh_entry(), _npsh_only_data(), Report export in every format — UC-09 (Word / LaTeX / PDF).  Qt-free: builds the, ``{"docx": xml, "tex": source, "html": source}`` of one export run. (+32 more)

### Community 12 - "BaseNode"
Cohesion: 0.17
Nodes (12): _capacity_m3h(), _head_quantity(), PipeSystemCurve, ndarray, System head at capacity ``q`` (scalar or array Quantity), in metres., Static head plus Darcy-Weisbach friction + minor losses of one pipe run.      ``, Reynolds number ``V * D / nu`` at capacity ``q``., Darcy friction factor (Swamee-Jain; ``64/Re`` for ``Re < 2300``). (+4 more)

### Community 13 - "DesignPoint"
Cohesion: 0.10
Nodes (68): asTolerances(), ComplianceForm(), HEADERS, Tolerances, VERDICT_TONE, CorrectionForm(), DEGREES, show() (+60 more)

### Community 14 - "GraphView"
Cohesion: 0.12
Nodes (9): GraphView, QPointF, Capture the current zoom + scene-space center for ``.pumpflow`` files., Restore a zoom + center previously captured by :meth:`view_state`., Apply a multiplicative zoom about the cursor, clamped to the band., Scroll the viewport by a pixel delta (touchpad / plain wheel pan)., Frame every node in the view (zoom extents), clamped to the zoom band., QGraphicsView (+1 more)

### Community 15 - "quantity_factory"
Cohesion: 0.10
Nodes (37): format_geometry(), _geometry_point(), One-line description of the set geometry parts, in the entered units., Temporary ``pump.TestPoint`` carrying the row's ΔP and the bench geometry., Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):     ``Head =, Head split into its terms, all in metres (tooltips / reports).      Returns ``{", row_head(), row_head_components() (+29 more)

### Community 16 - "units.py"
Cohesion: 0.18
Nodes (11): atm_in(), convert_display(), _convert_viscosity(), pint_str(), Pint unit string of a display label (``KeyError`` if the label is unknown)., Standard atmosphere expressed in the pressure display unit ``unit``.      Used t, Normalise a display value to the library's standard magnitude.      For density-, Re-express a value from one display unit to another (live combo switch). (+3 more)

### Community 17 - "unit_conversion.py"
Cohesion: 0.20
Nodes (9): curve(), design_point(), _dispose_graph_scenes(), Shared pytest fixtures for the ``pump`` library suite.  These were originally in, Cold water at ~997 kg/m³ — the reference fluid for the suite., A small, monotonic Q×H / Q×P performance curve at 1750 rpm., Rated/design point matching the curve's rated region (833 m³/h, 73 m)., Hand canvas items back to Python before their scenes are discarded.      Without (+1 more)

### Community 19 - "PerformanceFitter"
Cohesion: 0.14
Nodes (10): PerformanceFitter, ndarray, Lazily computes the polynomial regression coefficients for head vs. capacity., Lazily computes the polynomial regression coefficients for efficiency vs. capaci, Lazily computes the polynomial regression coefficients for power vs. capacity., Handles polynomial regression for performance metrics (head, efficiency, power),, Lazily computes and returns the capacity values as a NumPy array.          Retur, Lazily computes and returns the head values as a NumPy array.          Returns (+2 more)

### Community 20 - "PointNode"
Cohesion: 0.10
Nodes (40): CanvasHandle, CanvasProps, Flow(), nodeTypes, toDocEdge(), groupCatalog(), Toolbox(), CatalogEntry (+32 more)

### Community 23 - "Fluid"
Cohesion: 0.20
Nodes (12): _e(), _fmt(), HtmlReportGenerator, _image_uri(), Same number formatting as the docx report (``0.02f~P`` for quantities)., ``data:image/png;base64,...`` for a PNG path / BytesIO, else ``None``., Write the FAT report as a single self-contained ``.html`` file.      Parameters, Write ``output_file`` (``.html``); charts are embedded, no extra files. (+4 more)

### Community 25 - "Module Reference"
Cohesion: 0.06
Nodes (32): `base.BaseNode` + `PortSpec`, `BranchBundle` / `ReportBundle`, `CorrectedCurve`, `EdgeItem` *(QGraphicsPathItem)*, `FittedModel`, `GraphScene` *(QGraphicsScene)*, `GraphView` *(QGraphicsView)*, `MainWindow` (+24 more)

### Community 26 - "BasePoint"
Cohesion: 0.06
Nodes (51): Figure, color(), _colors(), contrast(), family(), font_px(), length(), _lengths() (+43 more)

### Community 27 - "PerformancePlotNode"
Cohesion: 0.08
Nodes (36): parse_decimal(), Parse a number that may use ``,`` or ``.`` as the decimal separator.      Heuris, json_from_signals(), _mag(), migrate(), _normalize_unit(), _num(), _opt() (+28 more)

### Community 31 - "QPushButton"
Cohesion: 0.06
Nodes (42): list, AcceptanceCriteria, Tolerance tables for one standard edition, optionally overlaid by a client., The unverified parts that bear on the performance-test verdict.          Exclude, Candidate, entry_from_dict(), _evaluate(), _opt_q() (+34 more)

### Community 32 - "conftest.py"
Cohesion: 0.06
Nodes (32): Engine, Pending, FakeWorker, WorkerLike, ApiFns, BeforeAfterRow, CallMessage, ComplianceRow (+24 more)

### Community 33 - "2. Findings in detail"
Cohesion: 0.07
Nodes (27): 1. Findings index, 2. Findings in detail, 3. Next-generation options, 4. Suggested first sprint (if Option A is accepted), Code Review — Toward the Next-Generation Tool, 🔴 F-01 — `acceptable_limits` raises instead of degrading, 🔴 F-02 — Head verdict applied at the wrong altitude, 🔴 F-03 — `test_data` builds ragged/crashing columns (+19 more)

### Community 35 - "ReportExportNode"
Cohesion: 0.22
Nodes (8): _label_or_canonical(), _pint(), _q_dec(), Pint string of a display label (a bare Pint string is accepted too)., ``(label, converted?)`` for a stored unit: its label, else canonical., On-disk ``{"value", "unit"}`` -> runtime ``{"value", "unit": label}``., Mechanical-run settings: channel units and criteria overrides.      ``columns``, RunLog

### Community 38 - "curve_fit.py"
Cohesion: 0.10
Nodes (15): _assert_same_results(), ``.pumpflow`` schema v2 — migration + settings codec (Sprint 2b).  Qt-free layer, Since S3, n / η / shut-off / NPSHa have their own unit keys: decode keeps     th, Since S3 the table works in per-column units: decode maps Pint strings to     di, Exact on structure, strings and booleans; numbers (stored as ``repr``     string, _scene(), _summary(), test_decode_keeps_stored_units_for_former_fixed_fields() (+7 more)

### Community 41 - "System Architecture Blueprint — CentrifugalPump"
Cohesion: 0.08
Nodes (24): 1.1 The system is two stacked subsystems, 1.2 Primary tech stack, 1.3 Layer responsibilities, 1. Executive system architecture, 2.1 Data flow (happy path), 2.2 System boundaries & integration touchpoints, 2. Component topology (visual map), 3. Core domains & design patterns (+16 more)

### Community 42 - "ReportBundle"
Cohesion: 0.12
Nodes (23): _dimensionless(), Create a new PerformanceCurve corrected from water to a viscous liquid         (, Float value of a dimensionless quantity (percent aware) or a number., b_parameter(), correction_factors(), viscosity =========  Viscosity correction of a water-test performance curve (HI, HI 9.6.7 viscosity parameter B (ANSI/HI 9.6.7-2010 Eq. 3, US-unit form).      Th, HI 9.6.7 correction factors ``(C_Q, C_H, C_eta)`` (ANSI/HI 9.6.7-2010 Eq. 4-7). (+15 more)

### Community 53 - "UI As-Built Register — pumpflow Workbench"
Cohesion: 0.08
Nodes (25): 10. Nodes and persistence added by 001_masterpiece, 11.1 Proposed: shared inputs without wires (not implemented), 11. Verdicts on the canvas (UI/UX review, 2026-11-17), 12. Toolbox, welcome and form states (UI/UX review, round 2, 2026-11-18), 1. Goal & Scope (As-Built), 2. Reference Workflow (from the notebook), 3. Data Model & Inter‑widget "Signals", 4. Library Binding (mandatory) (+17 more)

### Community 54 - "Tutorial — Running & Testing CentrifugalPump"
Cohesion: 0.10
Nodes (21): 1. Prerequisites, 2. Installation, 3. Running the `pump` library, 4. Running the `pumpflow` desktop app, 5. Testing, 6. Troubleshooting, 7. Quick reference, A first end-to-end run (+13 more)

### Community 55 - "theme.py"
Cohesion: 0.05
Nodes (50): One log line: clock ``time`` ("HH:MM") and ``{channel name: Q_}`` values.      A, RunReading, Formula explanations for the workbench (UC-10, educational mode).  One dictionar, PumpFlow — API 610 Pump Performance Workbench (Orange-style node canvas).  A thi, BaseNode, PortSpec, nodes.base ==========  The Qt-agnostic logic of a widget node.  A node declares, Helper: clear outputs and show an amber/idle status (UI_SPEC §7). (+42 more)

### Community 56 - "Spec-Driven Software Engineering: Adapting the CentrifugalPump Project to the OpenSpec Methodology"
Cohesion: 0.10
Nodes (19): 1.1 Specification-by-Example (SBE) and Behavior-Driven Development (BDD), 1.2 Living Documentation, 1.3 Traceability and Change Proposals, 1. Theoretical Fundamentals of OpenSpec, 2.1 Technical and Strategic Alignment, 2.2 Decision Matrix, 2. Evaluation: Should You Implement This?, 3.1 Step-by-Step "How" Guide (+11 more)

### Community 57 - "LatexReportGenerator"
Cohesion: 0.04
Nodes (45): dompurify, dompurify, NodeCardData, entry, PerformanceChart(), block, fit, npsh (+37 more)

### Community 58 - "test_persistence_roundtrip.py"
Cohesion: 0.06
Nodes (19): Create a new PerformanceCurve with all TestPoints scaled to `new_speed`., Create a new PerformanceCurve with all TestPoints scaled from the         impell, Access an individual TestPoint by index.          Parameters         ----------, Specialized version of the BasePoint class for handling test or operational data, Calculates the head generated due to pressure difference.          Returns, Calculates the fluid velocity at the pump inlet.          Returns         ------, Calculates the fluid velocity at the pump outlet.          Returns         -----, Calculates the head difference due to change in fluid velocity.          ``(v_ou (+11 more)

### Community 59 - "test_report_formats.py"
Cohesion: 0.09
Nodes (17): Liquid water at a given temperature.      Density is computed from a 4th-order p, Dynamic viscosity of liquid water, in cP.          Andrade-style exponential fit, Water, test_npsha_rejects_bare_pressure(), Library quantity spine — sprint 1 of project 001_masterpiece.  Asserts the new s, test_cst_quantity_factory_emits_no_warning(), test_pressure_absolute_to_gauge(), test_pressure_difference_is_reference_free() (+9 more)

### Community 60 - "RUN_AND_TEST.md"
Cohesion: 0.17
Nodes (17): kebab(), PORT_TYPES, portColor(), STATE_COLOR, STATE_GLYPH, stateColor(), statusBeside(), TONE_COLORS (+9 more)

### Community 61 - "CLAUDE.md"
Cohesion: 0.13
Nodes (14): Acceptance: one engine ([pump/acceptance.py](pump/acceptance.py), ADR 0012), Architecture: the `pump` library, Architecture: the `pumpflow` workbench, Common commands, Conventions and gotchas, Curves and transforms ([pump/performance_curve.py](pump/performance_curve.py)), Domain model, graphify (+6 more)

### Community 62 - "README.md"
Cohesion: 0.15
Nodes (11): Sprint index, Sprint template, Sprints, Acceptance criteria, Definition of Done, Files touched, Sprint S6 — Repo README + wrap (8 h), Tasks (≈ 8 h) (+3 more)

### Community 63 - "PerformanceCurve"
Cohesion: 0.08
Nodes (24): DOM, DOM.Iterable, ES2022, node, src, vite/client, vite.config.ts, compilerOptions (+16 more)

### Community 64 - "ExploreChartNode"
Cohesion: 0.08
Nodes (26): _find_col(), _next_time(), _norm_time(), paste_rows(), Index of the channel a pasted header names (exact, then prefix match)., Display label of a pasted header's unit for a channel of dimension ``dim``., MRT Log paste: tab- or ``;``-separated spreadsheet text -> readings.      An opt, _resolve_unit() (+18 more)

### Community 65 - "QLabel"
Cohesion: 0.10
Nodes (13): GraphScene, QPointF, Empty the scene in a controlled way before it is discarded.          ``EdgeItem`, Recompute every node in topological order and refresh the canvas., Serialize the canvas as a schema-v2 project document.          Node runtime sett, Rebuild the canvas from a project document (v1 is migrated to v2)., Connect an output port to an input port (orientation-tolerant)., QGraphicsScene (+5 more)

### Community 66 - "ARCHITECTURE.md"
Cohesion: 0.18
Nodes (12): _k_unit(), _length(), system_curve ============  System (pipe network) resistance curves (UC-03).  Two, Head at every capacity of ``q_array`` (a Quantity array), in metres., Fit ``H_static`` and ``k`` through two ``(q, h)`` points.          Examples, Pint unit ``m / (m**3/h)**n``., ``H(Q) = static_head + k * Q**exponent``.      Parameters     ----------     sta, SystemCurve (+4 more)

### Community 67 - "Build & Development Guide"
Cohesion: 0.15
Nodes (12): 1. Prerequisites, 2. Environment Setup, 3. Running the Applications, 4. Code Quality & Testing, 5. Building Documentation, 6. Creating a Distributable Package, Build & Development Guide, Formatting (+4 more)

### Community 68 - "NodeItem"
Cohesion: 0.27
Nodes (11): _fitted(), _rated(), Qt (offscreen) tests: Impeller Trim node, rated-point diameters, codec (sprint 1, test_rated_point_carries_impeller_diameters(), test_trim_dialog_opens(), test_trim_node_accepts_corrected_curve_input(), test_trim_node_default_idle_without_inputs(), test_trim_node_duty_mode_and_binding() (+3 more)

### Community 69 - "PortItem"
Cohesion: 0.08
Nodes (25): DesignPoint, Specific energy is the energy per unit mass of fluid.         It is calculated a, The mechanical power transferred to the liquid as it passes through the pump,, Calculates the outlet pressure based on inlet pressure and various heads., Calculates the head difference due to elevation.          Returns         ------, Calculates the fluid velocity at the pump inlet.          Returns         ------, Calculates the fluid velocity at the pump outlet.          Returns         -----, Calculates the head difference due to change in fluid velocity.          Returns (+17 more)

### Community 70 - "Dev Journey — your map when it feels like too much"
Cohesion: 0.17
Nodes (12): 2026-10-27, A use case is "in production" when…, Dev Journey — your map when it feels like too much, Latest Work Log, Read this when you're overwhelmed, The next sprints (sequenced for you), The one rule, The second rule — structure by domain, steer by use cases (+4 more)

### Community 71 - "test_pump_smoke.py"
Cohesion: 0.07
Nodes (25): Channel, ChannelResult, MechanicalRunCriteria, MechanicalRunLog, MechanicalRunResult, _parse_quantity(), _parse_time(), plot_mechanical_run() (+17 more)

### Community 72 - "Removal Map — scaffolding vs. product"
Cohesion: 0.18
Nodes (11): Bottom line, Lower-confidence candidate (verify before acting), Removal Map — scaffolding vs. product, Routine hygiene — clear the regenerable artifacts (not a removal), The principle, Tier 1 — Remove: vendored dev scaffolding (no longer referenced), Tier 2 — Consolidate: divergent duplicate → one gallery example, Tier 3 — Decide: dev-time smoke scaffolding (+3 more)

### Community 73 - "EdgeItem"
Cohesion: 0.24
Nodes (15): _node(), _rated(), Qt (offscreen) tests: NPSH node, codec round-trip, report section (sprint 8 / UC, Default rated point, re-pointed at the B-34004A duty (43.1 gpm, NPSHa 2.4 m)., _report_data(), test_b34004a_node_evaluates(), test_blank_sheet_is_invalid(), test_calculator_mode_matches_hand_formula() (+7 more)

### Community 74 - "AGENTS.md"
Cohesion: 0.20
Nodes (9): Commands (Match Repo Config), Fast Orientation, graphify, Hard Boundary, Persistence Guard, Repo Noise, Reports / Localization, Testing Gotchas (+1 more)

### Community 75 - "MVP use cases"
Cohesion: 0.12
Nodes (24): bisect_root(), NaturalCubicSpline, ndarray, r_squared(), fitting =======  Curve-fitting and root-finding helpers shared by the library an, Return ``(xs, ys)`` of ``n`` evenly spaced samples across the data., Coefficient of determination, R²., Root of ``f`` in ``[lo, hi]`` by bisection.      The interval must bracket a sig (+16 more)

### Community 76 - "Node & Banner State Colors"
Cohesion: 0.14
Nodes (18): main(), Build the example pump catalogue (``*.pumpcurve.json``) from the shipped project, build_scene(), Load ``project`` into an evaluated :class:`GraphScene` (offscreen Qt)., ``(rated, branches, settings)`` from the project's Report Export node.      ``co, report_inputs(), build_figure(), The regression fixture: MRT Log -> MRT Check (rated + fitted wired) ->     Repor (+10 more)

### Community 77 - "scene.py"
Cohesion: 0.09
Nodes (31): criteria_label(), Display label: edition label, plus `` + <client label>`` for an overlay., Display label for an edition key (+ optional client overlay)., standard_label(), assemble_report_data(), build_report_png(), cover_from_settings(), generate_docx() (+23 more)

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
Nodes (10): Building distributions, Capabilities, Centrifugal Pump, Developers (conda/mamba), Documentation, Installation & packaging, Quickstart, Regular users (+2 more)

### Community 82 - "pumpflow theming — editing the color scheme"
Cohesion: 0.19
Nodes (9): load_recent(), Path, QWidget, Build the left column listing the most recently opened projects.          Notes, Build the right column listing bundled example pipelines.          Only examples, Load a project from *path* and accept the dialog.          Parameters         --, Load a bundled example from *path* and accept the dialog.          Unlike :meth:, Open a system file-picker and load the chosen project. (+1 more)

### Community 83 - "UnitPrefs"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 1 — Library quantity spine, Tests

### Community 84 - "Architectural Analysis of the CentrifugalPump Project"
Cohesion: 0.22
Nodes (8): Architectural Analysis of the CentrifugalPump Project, Conclusion and Recommendation, Evaluating the Path Forward: Web and iOS, Introduction: A Tale of Two Halves, The Cornerstone: A Clean Separation of Concerns, The Current State: A Desktop-First, Expert-Oriented Paradigm, The iOS Version: Impractical and Not Recommended, The Web Version: Feasible but Demanding

### Community 85 - "export_cli.py"
Cohesion: 0.33
Nodes (5): Key decisions (2026-11-14), Levers / approach, Risks, The problem, Why 001_masterpiece exists

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
Cohesion: 0.05
Nodes (14): _docx_text(), Browser JSON API (``pumpflow.webapi``): plain JSON in, plain JSON out.  ``evalua, Edit one node "the web way": decode, patch runtime keys, encode, evaluate., Paragraph and table-cell texts of a .docx (what a reader sees)., A copy of ``doc`` whose Compliance node overrides the head tolerance., test_export_docx_has_the_texts_of_the_cli_docx(), test_export_html_states_the_tolerance_override(), test_web_edited_bench_geometry_stored_as_unset_when_off() (+6 more)

### Community 93 - "Audience"
Cohesion: 0.13
Nodes (19): ReportExportView, base64ToBytes(), downloadFile(), fileBlob(), printReport(), withPrintScript(), asView(), committed() (+11 more)

### Community 94 - "Sprint S1 — Test foundation + units spec (8 h)"
Cohesion: 0.16
Nodes (24): PerformanceLine, One vibration row: ``(tested, specified)`` in mm/s RMS for each region., One row of the hydraulic block (values in ``unit``; deviation a fraction)., VibrationLine, Bearing-housing vibration limits for the rated pump (``limits`` dict).      The, vibration_limits_for(), _annex_m_charts(), _band() (+16 more)

### Community 95 - "Sprint S2 — Pin the MVP physics (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S2 — Pin the MVP physics (8 h), Tasks (≈ 8 h)

### Community 96 - "Sprint S3 — GUI-openable case + persistence guard (8 h)"
Cohesion: 0.06
Nodes (40): desktop, diffs, expected, files, fixtureDir, here, pyDir, rel() (+32 more)

### Community 97 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.10
Nodes (24): compare_curves(), ComparisonRow, ComparisonTable, plot_comparison(), Relative delta ``(value - ref) / ref`` (NaN when the reference is zero)., Compare fitted curves at the given capacities.      Parameters     ----------, Overlay head, power and efficiency of several curves (three stacked panels)., Predictions of every curve at one capacity.      Attributes     ----------     q (+16 more)

### Community 98 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.14
Nodes (16): fit_model(), Polynomial coeffs (primary) + natural cubic splines (secondary)., CorrectedCurve, A ``pump.PerformanceCurve`` corrected to rated speed + rated fluid., fitted(), test_export_pumpcurve_binding_round_trip(), _fitted(), Qt (offscreen) tests: System Curve + Operating Point nodes (sprint 11 / UC-03, U (+8 more)

### Community 99 - ".__init__"
Cohesion: 0.04
Nodes (58): npsh3_from_sweep(), npsh_available(), npsh_margin(), NPSHrCurve, _parse_quantity(), plot_npsh(), BytesIO, ndarray (+50 more)

### Community 100 - "PumpLab — Documentation"
Cohesion: 0.06
Nodes (43): _client_overlays(), _edition_sort_key(), ``{key: (edition_table, standard_title)}`` for every shipped edition., ``{client: overlay_table}`` for every shipped client overlay., ``[(key, label), ...]`` for every shipped edition, sorted., ``[(client, label), ...]`` for every shipped client overlay., Load an edition, optionally merged with a client overlay.          The overlay r, _read_toml() (+35 more)

### Community 101 - "RatedPointInputNode"
Cohesion: 0.25
Nodes (18): η = hydraulic / breaking, in percent.  ``ρ`` is water at ``T_water`` by     defa, row_efficiency(), _g(), _rated(), Quantity-carrying signals and the binding's Quantity head/efficiency helpers (Qt, _row(), test_explicit_head_wins(), test_has_shutoff() (+10 more)

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
Cohesion: 0.14
Nodes (21): decode(), encode(), Runtime settings -> v2 on-disk settings (new dict; input untouched)., v2 on-disk settings -> runtime settings (new dict; input untouched)., _match_unit(), parse_unit_header(), Parse a column header such as ``"Q [gpm]"`` or ``"P_dis [psi g]"``.      Returns, test_codec_unknown_unit_converts_to_canonical() (+13 more)

### Community 107 - "Sprint S6 — Repo README + wrap (8 h)"
Cohesion: 0.09
Nodes (11): isWorkerMessage(), OfflineHandle, OfflineState, ProgressMessage, RegisterOptions, registerServiceWorker(), FakeContainer, FakeRegistration (+3 more)

### Community 108 - ".to_fluid"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 14 — Masterpiece polish: report, CI, docs, Tests

### Community 109 - "run"
Cohesion: 0.10
Nodes (17): closure, CORE, files, here, lock, manifest, norm(), npmPkg (+9 more)

### Community 111 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.09
Nodes (20): Limits, RMS, peak and the vendor's word, The high-speed chart (11th ed. Figure 34, 12th ed. Figure 35), Vibration: by pump type, and the high-speed chart, Where to measure depends on the pump type, Before you start, Sources, Training (+12 more)

### Community 112 - "ADR 0005 — Consolidate the `Point` hierarchy & remove broken code"
Cohesion: 0.50
Nodes (4): ADR 0005 — Consolidate the `Point` hierarchy & remove broken code, Consequences, Context, Decision

### Community 113 - "ADR 0006 — Replace `hasattr` duck-typing with an explicit schema"
Cohesion: 0.30
Nodes (15): code(), main(), md(), Generate the worked use-case notebooks of sprint 13.  Every notebook is written, tr01(), uc01(), uc02(), uc0304() (+7 more)

### Community 114 - "ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`"
Cohesion: 0.17
Nodes (13): _kinematic_viscosity(), Pipe-run system curve from Darcy-Weisbach with Swamee-Jain friction.          ``, Kinematic viscosity of liquid water (dynamic viscosity / density), in cSt., _hand_pipe_head(), System curve (UC-03): H = H_static + k·Q^n, two-point fit, Darcy–Weisbach pipe., Darcy–Weisbach + Swamee–Jain, written out independently of the library., test_curve_returns_quantity_array(), test_from_pipe_manual_fluid_kinematic_viscosity() (+5 more)

### Community 115 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.13
Nodes (15): Educational layer, MVP use cases, Priority summary, UC-00 — Work in the engineer's own measurement units ✅, UC-01 — Select a pump for given conditions ✅, UC-02 — Verify pump performance (FAT) ✅, UC-03 / UC-04 — System curve and operating point ✅, UC-05 — Check NPSH margin ✅ (+7 more)

### Community 116 - "ADR 0010 — Align versioning & declare GUI dependencies"
Cohesion: 0.50
Nodes (4): ADR 0010 — Align versioning & declare GUI dependencies, Consequences, Context, Decision

### Community 118 - "hline"
Cohesion: 0.10
Nodes (14): _kinematic_viscosity(), Create a new PerformanceCurve by assigning a new fluid to all TestPoints., Kinematic viscosity (cSt) of ``fluid``.      Reads ``kinematic_viscosity`` (e.g., Fluid, Returns a detailed string representation of the fluid., Returns a detailed string representation of the fluid's properties., A class to represent a fluid and its properties, enabling engineering calculatio, Initializes a Fluid object with converted physical properties.          Paramete (+6 more)

### Community 119 - "int_spin"
Cohesion: 0.27
Nodes (3): EdgeItem, QPointF, QGraphicsPathItem

### Community 120 - "line_edit"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 4 — Complete head (pressure + velocity + elevation), Tests

### Community 137 - "pumpflow/binding.py"
Cohesion: 0.08
Nodes (18): _empty_overrides(), SelectionNode, checkbox(), info_button(), line_edit(), QWidget, A spacing token of the design system, in pixels., Like row() but with a QComboBox as the suffix widget for unit selection. (+10 more)

### Community 150 - "pumpflow/binding.py"
Cohesion: 0.09
Nodes (16): _append_param(), ComplianceCheckNode, _Fallback, param_cells(), nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)  Inputs ``FittedMode, Stand-in rated point for the tolerance dialog before a RatedPoint is wired., The nine display cells of one parameter row (``_HEADERS`` order), as text., Banner (+8 more)

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
Cohesion: 0.28
Nodes (3): PerformancePlotNode, BytesIO, Y-limits converted from their display unit to canonical m / kW / %.

### Community 172 - "Banner"
Cohesion: 0.14
Nodes (11): _btn(), _bundle_json(), _mag(), _pick_dir(), _pick_file(), nodes.report_export — Report Export  (UI_SPEC §5.7)  Inputs: the shared ``RatedP, Settings of the Markdown Note nodes on the same canvas (may be empty)., Float magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``). (+3 more)

### Community 173 - "NaturalCubicSpline"
Cohesion: 0.14
Nodes (16): Return the canonical single-pump ``.pumpflow`` document (Qt-free, schema v2)., sample_project_doc(), b34004_scene(), _build_scene(), ``.pumpflow`` persistence guard — UC-02 / UC-09 (the workbench demo case).  Two, Sprint 10: diameter that puts B-34004A on its rated point lies inside the     da, A template row with no N / P / ΔP must be rejected by validation; before     the, test_b34004_cli_exports() (+8 more)

### Community 174 - ".__init__"
Cohesion: 0.10
Nodes (26): canvas.edge_item ================  A bezier link carrying a signal from an outpu, canvas package — reactive node-graph scene/view/items (PySide6)., canvas.node_item ================  The on-canvas representation of one workflow, canvas.port_item ================  A single connection point on a node (an Orang, body_font(), mono_font(), port_color(), _pt() (+18 more)

### Community 175 - "001_masterpiece — Loop Protocol"
Cohesion: 0.10
Nodes (15): Add the NPSH section (UC-05).          Parameters         ----------         doc, Add the pump comparison section (UC-08).          Parameters         ----------, Generates a report from predefined templates using the `python-docx` library., Retrieve the appropriate template file based on the selected language., Generates a report from a predefined template.          Parameters         -----, Add the cover block (title + project / client / tags / standard / date /, Add "Deviations and open points" (unverified criteria + open points)., Add the signature table (Role / Name / Signature / Date). (+7 more)

### Community 176 - ".paint"
Cohesion: 0.16
Nodes (8): _axis_scale(), ExploreChartNode, _mag(), Pin every left axis to the widest one so the plot frames (and the         shared, A capacity field (any capacity unit) + a table of the values each         fitted, A vertical guide + value label that follows the cursor across panes., Magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``)., ``(scale, display_unit)`` mapping canonical axis values to the preset's     disp

### Community 177 - "hline"
Cohesion: 0.32
Nodes (4): _length_opt(), _opt(), RatedPointInputNode, An optional length setting as a Quantity in mm (``None`` when unset/<= 0).

### Community 178 - ".to_speed"
Cohesion: 0.12
Nodes (14): Operating point of a fitted pump curve on a system curve., solve_operating_point(), ``PerformanceChecker.report_summary`` for one branch (Check's numbers).      ``t, report_summary_for(), FittedModel, OperatingPointResult, signals =======  Typed inter-widget payloads — the "signals" that flow along the, Polynomial coeffs (+ optional natural cubic splines) for H, P, η. (+6 more)

### Community 179 - ".__getitem__"
Cohesion: 0.17
Nodes (14): App(), EMPTY_DOC, FormPanel, spawnEngine(), Progress, root, parseProject(), projectFileName() (+6 more)

### Community 180 - ".import_data_file"
Cohesion: 0.18
Nodes (6): BasePoint, Returns a detailed string representation of the fluid's properties., Represents a system point with physical quantities.      Parameters     --------, Returns a detailed string representation of the fluid's properties., Returns a detailed string with fluid's properties., Returns a detailed string representation of the fluid's properties.

### Community 181 - ".__len__"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 10 — UC-07 Impeller trim, Tests

### Community 182 - ".__repr__"
Cohesion: 0.14
Nodes (22): _b34004a_log_settings(), _b34004a_settings(), _check(), _node(), Qt (offscreen) tests: MRT Log + MRT Check nodes, codec round-trip, the legacy on, An MRT Check fed by ``log_node``: ``(check node, outputs)``., MRT Log follows the Test Points layout: one unit combo above each     channel co, A witness-day template with times but no values must be invalid (no     verdict, (+14 more)

### Community 183 - "checkbox"
Cohesion: 0.10
Nodes (16): fit_table_headers(), PropertyDialog, QDialog, Maximise the window, or restore it to its previous size., Restore the last size / maximised state saved under ``key`` and save         it, On the first show, make table headers readable and, unless a size         was re, Size the window to its content: full width, height capped at 85 % of         the, Resize the window to fit header + body preferred size (opt-in).          Used by (+8 more)

### Community 184 - "export_cli.py"
Cohesion: 0.20
Nodes (26): _construction_rows(), _dev(), _header_rows(), _num(), _perf_header(), _perf_rows(), Path, Translate (+18 more)

### Community 185 - "PerformancePlotNode"
Cohesion: 0.12
Nodes (16): available_clients(), available_standards(), ``[(key, label)]`` of the editions the library offers., ``[(client, label)]`` of the client overlays the library offers., choice_options(), current_choice(), nodes.fluidpick — shared "which fluid drives this node" selection logic.  A flui, ``[(label, data)]`` pairs for :func:`pumpflow.nodes.ui.combo`.      A leading de (+8 more)

### Community 186 - ".absolute"
Cohesion: 0.11
Nodes (23): _fmt(), _latex_char(), latex_escape(), LatexReportGenerator, Path, One character for pdflatex: escaped, mapped, or a visible placeholder.      Char, Escape LaTeX special characters in ``text`` (converted with ``str``).      Also, Same number formatting as the docx report (``0.02f~P`` for quantities). (+15 more)

### Community 187 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.11
Nodes (21): Module, Path, Raw JSON read (also used for the §6.2 exchange JSON; never migrated)., read_json(), _in_process_states(), _module_level_imports(), Path, The graph engine path must work in an interpreter without Qt (Pyodide, sprint 2) (+13 more)

### Community 188 - "TestPointsTableNode"
Cohesion: 0.06
Nodes (46): Tooltip text ``"<title>\\n<text>"`` for ``key``.      Raises     ------     KeyE, tooltip(), banner_message(), ``(text, level)`` of the dialog banner (shared with the web form).      ``visc``, The "HI 9.6.7 factors" line of the dialog (``"—"`` without a correction)., viscous_summary(), _coeff_text(), Status verdict; ``not configured`` when no rule exists, provisional when     the (+38 more)

### Community 189 - "Data Formats"
Cohesion: 0.09
Nodes (37): utilities =========  This submodule provides unit conversion utilities to standa, comparison_sentence(), comparison_table(), cover_rows(), deviation_items(), Self-contained HTML report generation.  Consumes the **same** ``report_data`` di, LaTeX (``.tex``) and PDF report generation.  Consumes the **same** ``report_data, mechanical_run_duration_sentence() (+29 more)

### Community 190 - "line_edit"
Cohesion: 0.13
Nodes (5): Qt-free tests for the multi-unit spine: UNIT_OPTIONS, header parsing, codec., test_codec_decode_unlabelled_columns_go_canonical(), test_codec_roundtrip_test_points_columns(), test_test_points_us_columns_equal_si_columns(), _tp_runtime()

### Community 191 - "SystemCurveNode"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, jsdom, @testing-library/react, @types/node, @types/react, typescript, typescript-eslint (+9 more)

### Community 192 - ".is_empty"
Cohesion: 0.12
Nodes (15): LocalizationHelper, _parse_po(), performance_verdict(), Localized performance verdict; provisional when the criteria are unverified., One sentence listing user-overridden tolerances, or ``""`` when none.      ``ove, Minimal ``.po`` reader: ``{msgid: msgstr}`` for non-empty translations.      Han, Handles translation and localization using gettext.      Parameters     --------, Sets up gettext for localization.          Returns         -------         Calla (+7 more)

### Community 193 - ".density_rel"
Cohesion: 0.11
Nodes (13): PerformanceCurve, Any, Generates a report summarizing predicted performance values.                  Re, A container for handling a collection of TestPoint objects that share the same f, Predicts the head for a given flow (capacity) using the stored polynomial., Predicts the efficiency for a given flow (capacity) using the stored polynomial., Predicts the power for a given flow (capacity) using the stored polynomial., Best-efficiency point of the fitted curve.          The fitted efficiency polyno (+5 more)

### Community 194 - "._mark_clean"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 13 — UC-10 Educational mode + a worked notebook per use case, Tests

### Community 195 - "UnitPrefs"
Cohesion: 0.25
Nodes (4): canonical_unit(), The library's standard display label for a dimension (first option)., Holds the active project-level unit preset (SI / US / custom).      ``default_un, UnitPrefs

### Community 196 - "Pressures"
Cohesion: 0.18
Nodes (15): default_columns(), Column units of a fresh table: the active preset's display units., Flatten a ``TestPointSet`` to the node-settings ``columns`` / ``rows`` shape., testset_settings(), _col(), _head(), _header(), Qt (offscreen) tests: per-column units on the Test Points table. (+7 more)

### Community 197 - "correct_curve"
Cohesion: 0.21
Nodes (6): 001_masterpiece — Loop Protocol, 001_masterpiece — Pint end to end, every use case, FAT-grade acceptance, Changelog, Open items needing owner input, Standing rules (every sprint), Tracker

### Community 199 - ".__init__"
Cohesion: 0.18
Nodes (16): find_latex_engine(), Return the command used to build a PDF, or ``None`` when no TeX is found., _mm_s(), Maximum vibration per probe and flow region, tested vs specified.      Parameter, vibration_by_region(), _pts(), API 610 test data summary (Annex M / 8th-edition Appendix T)., _summaries() (+8 more)

### Community 200 - "check_npsh_set"
Cohesion: 0.20
Nodes (4): _code_text(), The design system is the single source of truth (pump/design/tokens.json).  - no, test_canvas_and_qss_follow_the_tokens(), test_every_token_is_used()

### Community 201 - "Data Formats"
Cohesion: 0.15
Nodes (6): diameter_for_duty(), Impeller diameter that makes ``curve`` pass through the duty ``(q, h)``.      Pa, Impeller trim — UC-07 (sprint 10).  Pins :meth:`pump.PerformanceCurve.to_diamete, test_diameter_for_duty_on_the_curve_is_the_reference(), test_diameter_for_duty_out_of_range_raises(), test_diameter_for_duty_recovers_known_diameter()

### Community 202 - ".available"
Cohesion: 0.25
Nodes (7): API, Assumptions, NPSH, NPSH available, NPSH required, NPSH3 and the margin, Two different rules, Worked notebook

### Community 203 - "_fmt_value"
Cohesion: 0.24
Nodes (14): overall_verdict_text(), Consolidated verdict of several pumps, in the Compliance node's words.      REJE, ComplianceResult, Per-parameter verdicts + the per-pump overall verdict., The verdict as every view shows it (canvas, Compliance, Report Export)., _view_report_export(), _approved(), _partial() (+6 more)

### Community 204 - "test_compliance_gui.py"
Cohesion: 0.16
Nodes (10): _opt(), _p_label(), PointNode, Return a positive float, or ``None`` when blank/zero/non-numeric., ``_opt``, normalise to the standard unit and wrap as a Quantity in     ``out_uni, The stored pressure display label, tolerating legacy Pint-string values., Derive head (m) from suction/discharge pressures + fluid density., _std_opt() (+2 more)

### Community 205 - "Pressures"
Cohesion: 0.25
Nodes (9): app_qss(), _logical_dpi(), _px_to_pt(), Rewrite every ``font-size: Npx`` as points at ``dpi`` logical DPI.      A font s, The global stylesheet with the resolved font families substituted in.      Font, The app stylesheet hands Qt point sizes, never pixel sizes.  A pixel-sized font, test_px_to_pt_keeps_on_screen_size(), test_qss_has_no_pixel_font_sizes() (+1 more)

### Community 206 - ".absolute"
Cohesion: 0.22
Nodes (13): export_test_summary(), Write the summaries; ``(paths, errors)`` like :func:`export_reports`., build_graph(), _logic_nodes(), main(), Headless report export: ``.pumpflow`` project → Word / LaTeX / PDF / HTML.  Usag, Load ``project`` into an evaluated :class:`pumpflow.engine.Graph` (no Qt)., The ``BaseNode`` logic objects of a Graph or a GraphScene. (+5 more)

### Community 207 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2, Tests

### Community 208 - "parse_standard_text"
Cohesion: 0.23
Nodes (11): _node(), Qt (offscreen) tests: Pump Selection node + dialog (sprint 12 / UC-01)., test_choice_selects_another_row(), test_default_instance_evaluates_without_a_catalogue(), test_empty_folder_is_idle(), test_gpm_ft_duty_gives_the_same_result(), test_no_pump_fits_is_invalid(), test_non_positive_duty_is_invalid() (+3 more)

### Community 209 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 1 — Headless graph engine, Tests

### Community 210 - "ADR 0006 — Replace `hasattr` duck-typing with an explicit schema"
Cohesion: 0.50
Nodes (4): ADR 0006 — Replace `hasattr` duck-typing with an explicit schema, Consequences, Context, Decision

### Community 211 - "PumpLab — Documentation"
Cohesion: 0.29
Nodes (6): API, Assumptions, Efficiency, Head components and efficiency, Total head, Worked notebooks

### Community 212 - "ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`"
Cohesion: 0.50
Nodes (4): ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`, Consequences, Context, Decision

### Community 213 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.22
Nodes (8): API, In the workbench, Mechanical running test, RMS, not peak, The checks, The log, The values shipped, Worked notebook

### Community 214 - "delta_pint"
Cohesion: 0.29
Nodes (6): API, Assumptions, Operating point, System curve, System curve and operating point, Worked notebook

### Community 215 - "upgrade_v1"
Cohesion: 0.26
Nodes (10): The status line without the segment the verdict pill already shows.      ``"B-1A, _status_beside(), _logic(), Qt (offscreen): the canvas verdict pill and first-open dialog sizing (UI/UX revi, test_badge_cleared_when_node_loses_input(), test_first_open_fits_table_headers(), test_judging_nodes_carry_a_badge(), test_override_adds_badge_note_and_clears_on_reset() (+2 more)

### Community 216 - "._load_project"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 3 — Unit choice on every GUI numeric field, Tests

### Community 217 - "test_head_gui.py"
Cohesion: 0.25
Nodes (8): 1. Ship it, 2. Before / at the B-34004B witness test (owner), 3. Confirm researched values against the standards (owner), 3b. Code review findings (2026-11-16), 3c. UI/UX review (2026-11-17), 4. Product follow-ups (candidate sprints for a 002 project), Never, Next steps (after 001_masterpiece)

### Community 218 - "SelectionCriteria"
Cohesion: 0.33
Nodes (5): API, Assumptions and validity, Equations, Viscosity correction (HI 9.6.7), Worked notebook

### Community 219 - "PumpLab — Documentation"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 2 — Node logic importable without Qt, Tests

### Community 221 - "Banner"
Cohesion: 0.21
Nodes (13): MrtCheckRow, MrtCheckView, Quantity, loadUnitOptions(), asOverrides(), DEFAULT_MIN_DURATION, DURATION_UNITS, g4() (+5 more)

### Community 222 - "YLimDisp"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 3 — JSON API for the browser (`pumpflow.webapi`), Tests

### Community 224 - "UnitColumnHeader"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 4 — Web scaffold + offline Pyodide spike (parity gate), Tests

### Community 225 - "_bundle_json"
Cohesion: 0.10
Nodes (28): location_of_key(), ``(Location, filtered)`` of a column key such as ``vib_gb_f``.      Raises     -, Return the chosen ``FluidSpec`` from ``specs``, or ``None`` for the node     def, resolve_fluid(), canonical_columns(), default_geometry_settings(), _geo_quantity(), geometry_from_settings() (+20 more)

### Community 227 - "RunLog"
Cohesion: 0.15
Nodes (7): _fmt_value(), The :class:`pump.acceptance.PerformanceVerdict` of this design point.          T, Parallel-operation rule: shut-off head / rated differential head         >= ``pa, Table of the rated-point checks (not of every raw test point), from         :met, Format a table cell: Pint quantities with ``0.02f~P``, others as text., The hydraulic power of the point.          Returns a cached `_hydraulic_power` v, The efficiency of the point.          Returns a cached `_efficiency` value if it

### Community 228 - "Affinity laws"
Cohesion: 0.29
Nodes (6): Affinity laws, API, Assumptions, Finding the speed or diameter for a duty, The laws, Worked notebooks

### Community 229 - "SelectionCriteria"
Cohesion: 0.29
Nodes (6): Changing the look, Contrast fixes made when the system was formalised (2026-11-17), Design system, Rules, The artifact, The families

### Community 230 - "SystemCurveNode"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S3 — GUI-openable case + persistence guard (8 h), Tasks (≈ 8 h)

### Community 231 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.29
Nodes (5): Qt (offscreen) test: criteria-aware compliance on the B-34004A reference project, _results(), scene(), test_project_evaluates_with_criteria_metadata(), test_reset_restores_criteria_defaults()

### Community 232 - "001_masterpiece — Loop Protocol"
Cohesion: 0.09
Nodes (27): make_node(), catalog(), Node kinds in toolbox order, with ports and the ``has_web_form`` flag., Node windows: maximise from the title bar, a header Maximize / Restore button on, test_button_and_double_click_toggle(), test_chart_windows_have_header_button(), test_every_node_window_has_min_max_buttons(), test_short_forms_have_no_header_button() (+19 more)

### Community 233 - "NPSHNode"
Cohesion: 0.17
Nodes (6): _blank_rows(), NPSHNode, A strip of unit combos laid out above a ``QTableWidget``'s columns., A unit combo for one table column (or ``span`` adjacent columns).      ``on_chan, UnitColumnHeader, UnitHeaderStrip

### Community 234 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S4 — Docstrings & doctests (8 h), Tasks (≈ 8 h)

### Community 235 - "Data Formats"
Cohesion: 0.17
Nodes (9): 60-second orientation, CentrifugalPump — Documentation, Deeper references (pumpflow UI), Start here, Acceptance criteria, Definition of Done, Files touched, Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h) (+1 more)

### Community 236 - "Banner"
Cohesion: 0.33
Nodes (6): Back-compatibility, Extending it, How it is wired, Multi-unit handling — design philosophy, Pint end to end (001_masterpiece), The invariants

### Community 237 - ".deviation"
Cohesion: 0.13
Nodes (15): add(), bg, color(), colorResolve, fg, here, lines, out (+7 more)

### Community 239 - "YLimDisp"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 5 — Canvas: open, view, wire, save, Tests

### Community 240 - "CentrifugalPump — Documentation"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 6 — Witness forms I: Rated Point, Fluid, Test Points, Correction, Fit, Compliance, Tests

### Community 241 - "_bundle_json"
Cohesion: 0.25
Nodes (6): ABC, ImprovedQuantity, Defines an abstract interface for unit conversion.          Methods     -------, Implements unit conversion based on predefined standard units., Converts a given quantity to its corresponding standard unit.          Parameter, UnitConverterInterface

### Community 242 - "TestRow"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 7 — Witness forms II: plots, NPSH, MRT Log, MRT Check, Note, Tests

### Community 243 - "QSettings"
Cohesion: 0.18
Nodes (10): _mag_or(), app ===  The PumpFlow main window: a node toolbox, the reactive canvas, the menu, Magnitude of an optional Quantity in ``unit``, or ``default`` when ``None``., run(), Run PumpFlow:  python -m pumpflow, grouped_node_kinds(), ``NODE_KINDS`` split into :data:`NODE_GROUPS`; any kind not listed goes     into, init_fonts() (+2 more)

### Community 244 - "Disp"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 8 — Reports in the browser + installable offline app, Tests

### Community 245 - "Acceptance tolerances (data-driven)"
Cohesion: 0.25
Nodes (7): Acceptance tolerances (data-driven), Client overlay: Petrobras N-553 rev E, How it is wired, One engine, three outcomes, The values, by edition, The `verified` flag, What is checked

### Community 246 - ".verdict"
Cohesion: 0.18
Nodes (11): marked, pyodide, react, react-dom, dependencies, marked, pyodide, react (+3 more)

### Community 247 - ".import_data_file"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 9 — CI parity job, docs and training, Tests

### Community 248 - ".absolute"
Cohesion: 0.22
Nodes (9): scripts, build, check, dev, parity, prebuild, predev, tokens (+1 more)

### Community 249 - "Pressures"
Cohesion: 0.24
Nodes (9): _convert(), _norm(), settings_codec ==============  Qt-free translation between node **runtime settin, Test-points table: runtime ``columns`` (labels) <-> on-disk ``columns`` (Pint)., v1 runtime shape (``unit`` + canonical rows) -> ``columns`` shape., Normalise the compact ``%`` spelling to Pint's ``percent``., Convert ``value`` from ``src`` to ``dst``; untouched when the units agree., _same_unit() (+1 more)

### Community 250 - "_disk_unit"
Cohesion: 0.16
Nodes (10): 002_web — Motivation, Approach, Decisions, Open decisions, Problem, Risks, 002_web — Loop Protocol, 002_web — PumpFlow in the browser (offline, witness flow first) (+2 more)

### Community 251 - "_pint"
Cohesion: 0.20
Nodes (8): _disk_unit(), _fmt(), _q_enc(), The unit string written to disk for a display label.      Compact Pint spelling, Optional ``[lo, hi]`` axis limits with a runtime unit label., Runtime ``{"value", "unit": label}`` -> on-disk ``{"value", "unit": pint}``., Compact (``~C``) Pint spelling, as produced by ``pump.quantity_io.to_json``., YLimDisp

### Community 252 - "Sprint S1 — Test foundation + units spec (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S1 — Test foundation + units spec (8 h), Tasks (≈ 8 h)

### Community 253 - ".showEvent"
Cohesion: 0.06
Nodes (31): _band(), _band_for(), CheckRow, deviation(), evaluate_performance(), head_rises_to_shutoff(), _high_speed(), _limit() (+23 more)

### Community 254 - "001_masterpiece — Loop Protocol"
Cohesion: 0.33
Nodes (6): Capabilities at a glance, Documentation map, Project layout, PumpLab — Documentation, Quick start, The seven widgets

### Community 255 - "Sprint S0 — Product context & sprint scaffold (8 h)"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S0 — Product context & sprint scaffold (8 h), Tasks (≈ 8 h)

### Community 256 - "export_pumpcurve"
Cohesion: 0.07
Nodes (47): Exception, BindingError, _has_eff(), _mag(), make_fluid(), make_rated_fluid(), pumpflow.binding._common  Shared adapters: errors, fluids, the rated design poin, Human-readable wrapper around library/validation failures (UI_SPEC §7). (+39 more)

### Community 257 - ".from_table"
Cohesion: 0.40
Nodes (5): 1 · Data-exchange JSON (UI_SPEC §6.2), 2 · Project file — `.pumpflow` (UI_SPEC §6.1), 3 · Report outputs, Data Formats, Field reference

### Community 258 - "Sprint S6 — Repo README + wrap (8 h)"
Cohesion: 0.20
Nodes (7): NPSHTable, parse_standard_text(), NPSH-node settings: per-column units of the NPSHr table + the margin override., ``(standard_key, client)`` from the free-text rated-point ``standard``.      ``", Normalise a v1 runtime-shaped settings dict before :func:`encode`.      Missing, upgrade_v1(), test_parse_standard_text()

### Community 259 - "ADR 0012 — One performance-verdict engine, no silent passes"
Cohesion: 0.50
Nodes (4): ADR 0012 — One performance-verdict engine, no silent passes, Consequences, Context, Decision

### Community 260 - "SelectionResult"
Cohesion: 0.22
Nodes (7): check_mark_path(), Path of the checked-checkbox tick (an SVG in the ``check-mark`` token colour)., UI/UX review, round 2 (2026-11-18): disabled fields read as disabled, a tick in, test_geometry_rows_disabled_until_applied(), test_rated_point_cover_label_is_named(), test_stylesheet_has_disabled_state_and_tick(), test_welcome_wording()

### Community 261 - "Banner"
Cohesion: 0.31
Nodes (4): QDialog, QFrame, Splash / start-screen modal shown over the main window at launch.      The calle, WelcomeDialog

### Community 262 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.50
Nodes (4): ADR 0002 — Fix the `pint` `NameError` in the units foundation, Consequences, Context, Decision

### Community 263 - ".components_available"
Cohesion: 0.50
Nodes (4): ADR 0009 — Promote `mathx` into the `pump` library, Consequences, Context, Decision

### Community 264 - ".is_empty"
Cohesion: 0.25
Nodes (3): DOMMatrixReadOnlyStub, g, ResizeObserverStub

### Community 265 - "package.json"
Cohesion: 0.29
Nodes (6): engines, node, name, private, type, version

### Community 266 - "Audience"
Cohesion: 0.33
Nodes (6): Audience, Primary — Performance test / FAT engineer, Repo-vs-spec discrepancy, Roles explicitly out of scope, Secondary — Application / selection engineer *(pending owner sign-off)*, Tertiary — Student / learner *(pending owner sign-off)*

### Community 267 - "UnitColumnHeader"
Cohesion: 0.50
Nodes (4): ADR 0001 — Establish an automated test harness, Consequences, Context, Decision

### Community 268 - ".from_table"
Cohesion: 0.22
Nodes (4): Disp, OptDisp, Value with a runtime display label: ``key`` + ``unit_key`` <-> quantity., Optional :class:`Disp`: an unset (``None``) value is **omitted** on disk.      T

### Community 269 - "available_clients"
Cohesion: 0.25
Nodes (8): Build, Install and work offline, PumpFlow in the browser, Scope, Serve, Troubleshooting, Updating, What stays on the machine

### Community 274 - "_vibration_keys"
Cohesion: 0.08
Nodes (32): ``{"overall": Q_, "filtered": Q_, "basis": str}`` for a pump type         (OH/BB, HighSpeedRule, limit_group(), Location, locations_for(), plot_high_speed_chart(), pump_family(), pump.vibration ==============  API 610 pump types and where their bearing-housin (+24 more)

### Community 276 - "SelectionCriteria"
Cohesion: 0.29
Nodes (5): Preferred operating region (POR) used by pump selection (UC-01).      Attributes, True when both bounds are set., Build from a TOML ``selection`` table (missing bounds stay ``None``)., SelectionCriteria, test_custom_por_changes_the_flag()

### Community 277 - "Pressures"
Cohesion: 0.38
Nodes (3): _atm(), Pressures, Pressures sharing one runtime unit label + g/a reference -> ``{value, unit, ref}

### Community 282 - "render"
Cohesion: 0.33
Nodes (3): Replace ``@token`` and ``@fs-<style>`` placeholders in ``template``.      Colour, render(), MarkdownNoteNode

### Community 283 - "RatedPoint"
Cohesion: 0.33
Nodes (4): RatedPoint, The rated (design) point + rated fluid, shared by every pump branch., Relative density (SG) — the user-facing density form., UI_SPEC §5.1 validation: Q ≥ 0, H > 0, N > 0, P > 0.

### Community 284 - "sw-template.js"
Cohesion: 0.53
Nodes (4): batches(), BYTES, notify(), PRECACHE

### Community 285 - "ADR 0011 — Schema v2: value + unit persistence"
Cohesion: 0.40
Nodes (5): ADR 0011 — Schema v2: value + unit persistence, Alternatives considered, Consequences, Context, Decision

### Community 286 - "_default_columns"
Cohesion: 0.40
Nodes (3): _default_columns(), _default_rows(), The witness-sheet channels: flow, vibration (overall and filtered, both     limi

### Community 287 - "welcome.py"
Cohesion: 0.40
Nodes (4): welcome =======  Start-screen dialog shown on application launch.  Presents Rece, Two-line label of a recent project: file name, then folder · modified date., recent_label(), test_recent_label_shows_folder_and_date()

## Knowledge Gaps
- **821 isolated node(s):** `centrifugal-pump`, `name`, `version`, `private`, `type` (+816 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **80 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Q` connect `.__init__` to `export_pumpcurve`, `.density_rel`, `ARCHITECTURE.md`, `BasePoint`, `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `PortItem`, `_bundle_json`, `test_pump_smoke.py`, `BaseNode`, `.compute`, `quantity_factory`, `_bundle_json`, `Banner`, `test_persistence_roundtrip.py`, `test_report_formats.py`, `.showEvent`, `QPushButton`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `make_node()` connect `001_masterpiece — Loop Protocol` to `registry.py`, `MainWindow`, `SelectionResult`, `quantity_factory`, `_vibration_keys`, `curve_fit.py`, `NaturalCubicSpline`, `.__repr__`, `theme.py`, `TestPointsTableNode`, `ExploreChartNode`, `QLabel`, `NodeItem`, `Pressures`, `.__init__`, `EdgeItem`, `Node & Banner State Colors`, `.absolute`, `parse_standard_text`, `upgrade_v1`, `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `Sprint S0 — Product context & sprint scaffold (8 h)`, `QSettings`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Why does `row_head_components()` connect `quantity_factory` to `export_pumpcurve`, `_bundle_json`, `.__init__`, `test_report_formats.py`, `TestPointsTableNode`?**
  _High betweenness centrality (0.035) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `make_node()` (e.g. with `.__init__()` and `build_scene()`) actually correct?**
  _`make_node()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `BaseNode` (e.g. with `ComplianceCheckNode` and `_Fallback`) actually correct?**
  _`BaseNode` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GraphScene` (e.g. with `EdgeItem` and `NodeItem`) actually correct?**
  _`GraphScene` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `PerformanceCurve` (e.g. with `Candidate` and `Catalogue`) actually correct?**
  _`PerformanceCurve` has 22 INFERRED edges - model-reasoned connections that need verification._