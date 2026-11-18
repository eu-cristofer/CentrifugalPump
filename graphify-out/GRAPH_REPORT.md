# Graph Report - CentrifugalPump  (2026-11-18)

## Corpus Check
- 212 files · ~192,252 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3225 nodes · 6334 edges · 260 communities (192 shown, 68 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 374 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3904927e`
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
- Sprint S0 — Product context & sprint scaffold (8 h)
- Sprint S6 — Repo README + wrap (8 h)
- export_pumpcurve
- .from_table
- Banner
- ADR 0012 — One performance-verdict engine, no silent passes

## God Nodes (most connected - your core abstractions)
1. `make_node()` - 89 edges
2. `BaseNode` - 55 edges
3. `PerformanceCurve` - 48 edges
4. `quantity_factory()` - 47 edges
5. `TestPoint` - 46 edges
6. `PerformanceChecker` - 45 edges
7. `GraphScene` - 45 edges
8. `RatedPoint` - 45 edges
9. `Fluid` - 38 edges
10. `Water` - 37 edges

## Surprising Connections (you probably didn't know these)
- `test_checker_head_tolerance_band()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_pump_smoke.py → pump/performance_curve.py
- `test_checker_shutoff_tolerance_tier()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_pump_smoke.py → pump/performance_curve.py
- `test_report_summary_keys()` --calls--> `PerformanceChecker`  [INFERRED]
  tests/test_pump_smoke.py → pump/performance_curve.py
- `test_water_100c_vapour_pressure()` --calls--> `Water`  [INFERRED]
  tests/test_quantity_spine.py → pump/utilities/fluid.py
- `test_water_20c_kinematic_viscosity()` --calls--> `Water`  [INFERRED]
  tests/test_quantity_spine.py → pump/utilities/fluid.py

## Import Cycles
- 1-file cycle: `pump/__init__.py -> pump/__init__.py`
- 1-file cycle: `pump/utilities/__init__.py -> pump/utilities/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/test_points.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/performance_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/mechanical_run.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/fluid.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/report_export.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/compliance.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/operating_point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/explore_plot.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/trim.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/correction.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/npsh.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/system_curve.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/curve_fit.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/markdown_note.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/selection.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/mechanical_run_check.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/point.py -> pumpflow/nodes/__init__.py`
- 3-file cycle: `pumpflow/nodes/__init__.py -> pumpflow/nodes/registry.py -> pumpflow/nodes/rated_point.py -> pumpflow/nodes/__init__.py`

## Communities (260 total, 68 thin omitted)

### Community 0 - "GraphScene"
Cohesion: 0.12
Nodes (10): NodeItem, QGraphicsObject, GraphScene, QPointF, Empty the scene in a controlled way before it is discarded.          ``EdgeItem`, Recompute every node in topological order and refresh the canvas., Serialize the canvas as a schema-v2 project document.          Node runtime sett, Rebuild the canvas from a project document (v1 is migrated to v2). (+2 more)

### Community 1 - "app.py"
Cohesion: 0.15
Nodes (15): _kinematic_viscosity(), Pipe-run system curve from Darcy-Weisbach with Swamee-Jain friction.          ``, Q_, Liquid water at a given temperature.      Density is computed from a 4th-order p, Dynamic viscosity of liquid water, in cP.          Andrade-style exponential fit, Kinematic viscosity of liquid water (dynamic viscosity / density), in cSt., Saturation (vapour) pressure of water, absolute, in kPa.          Source: IAPWS-, Water (+7 more)

### Community 2 - "binding.py"
Cohesion: 0.18
Nodes (22): check_compliance(), criteria_for(), default_tolerances(), The ``AcceptanceCriteria`` selected by the rated point.      Falls back to the l, Criteria-default tolerances exposed as editable fields (UI_SPEC §5.6).      Both, Evaluate API 610 deviations & verdict.      A thin adapter: the verdict is :func, ParameterCheck, One row of the compliance table. (+14 more)

### Community 3 - "WelcomeDialog"
Cohesion: 0.12
Nodes (12): affinity_intersection(), diameter_for_duty(), _duty_values(), Q_, trim ====  Impeller trim helpers (UC-07).  Method ------ Pure **diameter affinit, Impeller diameter that makes ``curve`` pass through the duty ``(q, h)``.      Pa, ``(q_m3h, h_m)`` floats of a duty; ``ValueError`` unless both are > 0., Capacity ``Q1`` where the affinity parabola through ``(q, h)`` meets ``curve``. (+4 more)

### Community 4 - "registry.py"
Cohesion: 0.07
Nodes (41): color(), A colour token's value, aliases (``"{other}"``) resolved., PumpFlow — API 610 Pump Performance Workbench (Orange-style node canvas).  A thi, PortSpec, nodes.base ==========  The Qt-agnostic logic of a widget node.  A node declares, nodes.compliance — API 610 Compliance Check  (UI_SPEC §5.6)  Inputs ``FittedMode, nodes.correction — Speed / Affinity Correction  (UI_SPEC §5.3)  Inputs ``RatedPo, nodes.curve_fit — Curve Fit  (UI_SPEC §5.4)  Input ``CorrectedCurve`` → output ` (+33 more)

### Community 5 - "MainWindow"
Cohesion: 0.19
Nodes (6): MainWindow, Switch the project's display-unit preset (File-level preference)., Reflect the active ``units.PREFS`` preset in the Units menu check., Flag the session as having unsaved changes.          Appends an asterisk to the, QAction, QMainWindow

### Community 6 - "PerformanceChecker"
Cohesion: 0.10
Nodes (20): PerformanceChecker, True when no curve point lies below ``shutoff_extrapolation_q_fraction``, Generates a summary table checking if performance values are within limits., A class to check and validate the performance of a system based on a design poin, test_acceptable_limits_argument_warns(), test_checker_and_engine_agree(), test_checker_limits_match_default_criteria(), test_f02_check_summary_lists_rated_rows_only() (+12 more)

### Community 7 - "UnitField"
Cohesion: 0.16
Nodes (6): link_pressure_fields(), PressureField, A pressure field: ``UnitField("pressure")`` plus a gauge/absolute combo.      Co, ``fn(kind, field)`` is called with ``kind`` in ``{"unit", "ref"}``., Keep two pressure fields on the same unit and g/a reference., Select ``label``; ``on_change`` is only called when ``notify``.

### Community 8 - "TestPoint"
Cohesion: 0.06
Nodes (37): Preferred operating region (POR) used by pump selection (UC-01).      Attributes, True when both bounds are set., Build from a TOML ``selection`` table (missing bounds stay ``None``)., SelectionCriteria, Catalogue, CatalogueEntry, entry_to_dict(), _has_eff() (+29 more)

### Community 9 - "Q_"
Cohesion: 0.10
Nodes (31): _has_eff(), _mag(), make_rated_fluid(), pumpflow.binding._common  Shared adapters: errors, fluids, the rated design poin, Construct the rated ``Fluid`` from the rated point., Density of water at ``temp_c`` (°C) via ``pump.Water`` — kg/m³ (UC-00)., Dynamic viscosity of liquid water at ``temp_c`` (°C) — cP.      Delegates to ``p, Kinematic viscosity of liquid water at ``temp_c`` (°C) — cSt.      Delegates to (+23 more)

### Community 10 - "SpeedCorrectionNode"
Cohesion: 0.10
Nodes (19): canvas.edge_item ================  A bezier link carrying a signal from an outpu, canvas package — reactive node-graph scene/view/items (PySide6)., PortItem, QGraphicsObject, QPointF, QRectF, canvas.port_item ================  A single connection point on a node (an Orang, canvas.scene ============  The reactive node-graph scene.  - holds :class:`NodeI (+11 more)

### Community 11 - "ReportGenerator"
Cohesion: 0.10
Nodes (39): export_reports(), Write the report in every requested format.      Returns ``(paths, errors)``: ``, _mechanical_run_entry(), _mr_only_data(), _npsh_entry(), _npsh_only_data(), Report export in every format — UC-09 (Word / LaTeX / PDF).  Qt-free: builds the, ``{"docx": xml, "tex": source, "html": source}`` of one export run. (+31 more)

### Community 12 - "BaseNode"
Cohesion: 0.13
Nodes (18): _capacity_m3h(), _head_quantity(), _k_unit(), _length(), PipeSystemCurve, ndarray, Q_, system_curve ============  System (pipe network) resistance curves (UC-03).  Two (+10 more)

### Community 13 - "DesignPoint"
Cohesion: 0.16
Nodes (12): HighSpeedRule, plot_high_speed_chart(), API 610: limits calculated from the basic limits are rounded to two     signific, The curve family of the high-speed vibration figure.      ``v_u = base * (n / n_, True above the reference speed or the reference power per stage., Unrounded overall limit in mm/s (the chart's continuous curve)., Overall limit (mm/s RMS, two significant figures)., Discrete-frequency limit: ``discrete_ratio`` x the overall limit. (+4 more)

### Community 14 - "GraphView"
Cohesion: 0.12
Nodes (9): GraphView, QPointF, Capture the current zoom + scene-space center for ``.pumpflow`` files., Restore a zoom + center previously captured by :meth:`view_state`., Apply a multiplicative zoom about the cursor, clamped to the band., Scroll the viewport by a pixel delta (touchpad / plain wheel pan)., Frame every node in the view (zoom extents), clamped to the zoom band., QGraphicsView (+1 more)

### Community 15 - "quantity_factory"
Cohesion: 0.15
Nodes (25): format_geometry(), One-line description of the set geometry parts, in the entered units., Head split into its terms, all in metres (tooltips / reports).      Returns ``{", row_head_components(), BenchGeometry, Optional test-bench geometry completing the head (sprint 4).      ``H = ΔP/(ρ·g), True when no field is set (the head is then ΔP/(ρ·g) only)., ``(velocity, elevation)`` — which head terms can be evaluated. (+17 more)

### Community 16 - "units.py"
Cohesion: 0.18
Nodes (11): atm_in(), convert_display(), _convert_viscosity(), pint_str(), Pint unit string of a display label (``KeyError`` if the label is unknown)., Standard atmosphere expressed in the pressure display unit ``unit``.      Used t, Normalise a display value to the library's standard magnitude.      For density-, Re-express a value from one display unit to another (live combo switch). (+3 more)

### Community 17 - "unit_conversion.py"
Cohesion: 0.12
Nodes (12): Fluid, Returns a detailed string representation of the fluid., Returns a detailed string representation of the fluid's properties., A class to represent a fluid and its properties, enabling engineering calculatio, Initializes a Fluid object with converted physical properties.          Paramete, Returns a detailed string with fluid's properties., test_mixed_fluid_curve_is_rejected(), test_fluid_density_canonicalizes_to_kg_per_m3() (+4 more)

### Community 19 - "PerformanceFitter"
Cohesion: 0.14
Nodes (10): PerformanceFitter, ndarray, Lazily computes the polynomial regression coefficients for head vs. capacity., Lazily computes the polynomial regression coefficients for efficiency vs. capaci, Lazily computes the polynomial regression coefficients for power vs. capacity., Handles polynomial regression for performance metrics (head, efficiency, power),, Lazily computes and returns the capacity values as a NumPy array.          Retur, Lazily computes and returns the head values as a NumPy array.          Returns (+2 more)

### Community 20 - "PointNode"
Cohesion: 0.14
Nodes (12): _client_overlays(), _edition_sort_key(), ``{key: (edition_table, standard_title)}`` for every shipped edition., ``{client: overlay_table}`` for every shipped client overlay., ``[(key, label), ...]`` for every shipped edition, sorted., ``[(client, label), ...]`` for every shipped client overlay., _read_toml(), _standards() (+4 more)

### Community 23 - "Fluid"
Cohesion: 0.20
Nodes (12): _e(), _fmt(), HtmlReportGenerator, _image_uri(), Same number formatting as the docx report (``0.02f~P`` for quantities)., ``data:image/png;base64,...`` for a PNG path / BytesIO, else ``None``., Write the FAT report as a single self-contained ``.html`` file.      Parameters, Write ``output_file`` (``.html``); charts are embedded, no extra files. (+4 more)

### Community 25 - "Module Reference"
Cohesion: 0.06
Nodes (32): `base.BaseNode` + `PortSpec`, `BranchBundle` / `ReportBundle`, `CorrectedCurve`, `EdgeItem` *(QGraphicsPathItem)*, `FittedModel`, `GraphScene` *(QGraphicsScene)*, `GraphView` *(QGraphicsView)*, `MainWindow` (+24 more)

### Community 26 - "BasePoint"
Cohesion: 0.12
Nodes (29): Figure, _arrow_x(), _band_axis(), _callout(), _dimension(), _fmt(), _hatch_limit(), _host() (+21 more)

### Community 27 - "PerformancePlotNode"
Cohesion: 0.08
Nodes (35): _d(), app ===  The PumpFlow main window: a node toolbox, the reactive canvas, the menu, run(), Run PumpFlow:  python -m pumpflow, default_columns(), Column units of a fresh table: the active preset's display units., Flatten a ``TestPointSet`` to the node-settings ``columns`` / ``rows`` shape., testset_settings() (+27 more)

### Community 31 - "QPushButton"
Cohesion: 0.07
Nodes (39): list, AcceptanceCriteria, Tolerance tables for one standard edition, optionally overlaid by a client., The unverified parts that bear on the performance-test verdict.          Exclude, Candidate, entry_from_dict(), _evaluate(), _opt_q() (+31 more)

### Community 32 - "conftest.py"
Cohesion: 0.08
Nodes (26): One log line: clock ``time`` ("HH:MM") and ``{channel name: Q_}`` values.      A, RunReading, build_log(), _cell(), _channel_rows(), _empty_overrides(), MechanicalRunCheckNode, nodes.mechanical_run_check — MRT Check  (UC-11)  Judges a mechanical-run log aga (+18 more)

### Community 33 - "2. Findings in detail"
Cohesion: 0.11
Nodes (19): 2. Findings in detail, 🔴 F-01 — `acceptable_limits` raises instead of degrading, 🔴 F-02 — Head verdict applied at the wrong altitude, 🔴 F-03 — `test_data` builds ragged/crashing columns, 🔴 F-04 — `to_fluid` is stricter and quieter than `to_speed`, 🟠 F-05 — Two acceptance criteria that can disagree at the edge, 🟠 F-06 — Fit degree is unvalidated and inconsistent, 🟠 F-07 — Shutoff head is an unlabeled extrapolation (+11 more)

### Community 35 - "ReportExportNode"
Cohesion: 0.24
Nodes (9): _convert(), _norm(), settings_codec ==============  Qt-free translation between node **runtime settin, Test-points table: runtime ``columns`` (labels) <-> on-disk ``columns`` (Pint)., v1 runtime shape (``unit`` + canonical rows) -> ``columns`` shape., Normalise the compact ``%`` spelling to Pint's ``percent``., Convert ``value`` from ``src`` to ``dst``; untouched when the units agree., _same_unit() (+1 more)

### Community 38 - "curve_fit.py"
Cohesion: 0.07
Nodes (30): migrate(), Path, Raw JSON read (also used for the §6.2 exchange JSON; never migrated)., Upgrade a ``.pumpflow`` document to schema v2 (pure, idempotent).      Returns a, Split legacy one-node mechanical runs into **MRT Log** + **MRT Check**.      Bef, Read a ``.pumpflow`` project file and migrate it to the current schema., read_json(), read_project() (+22 more)

### Community 41 - "System Architecture Blueprint — CentrifugalPump"
Cohesion: 0.08
Nodes (24): 1.1 The system is two stacked subsystems, 1.2 Primary tech stack, 1.3 Layer responsibilities, 1. Executive system architecture, 2.1 Data flow (happy path), 2.2 System boundaries & integration touchpoints, 2. Component topology (visual map), 3. Core domains & design patterns (+16 more)

### Community 42 - "ReportBundle"
Cohesion: 0.13
Nodes (22): b_parameter(), correction_factors(), Q_, HI 9.6.7 viscosity parameter B (ANSI/HI 9.6.7-2010 Eq. 3, US-unit form).      Th, HI 9.6.7 correction factors ``(C_Q, C_H, C_eta)`` (ANSI/HI 9.6.7-2010 Eq. 4-7)., _b34004a_set(), eff_curve(), _g() (+14 more)

### Community 53 - "UI As-Built Register — pumpflow Workbench"
Cohesion: 0.08
Nodes (25): 10. Nodes and persistence added by 001_masterpiece, 11.1 Proposed: shared inputs without wires (not implemented), 11. Verdicts on the canvas (UI/UX review, 2026-11-17), 12. Toolbox, welcome and form states (UI/UX review, round 2, 2026-11-18), 1. Goal & Scope (As-Built), 2. Reference Workflow (from the notebook), 3. Data Model & Inter‑widget "Signals", 4. Library Binding (mandatory) (+17 more)

### Community 54 - "Tutorial — Running & Testing CentrifugalPump"
Cohesion: 0.10
Nodes (21): 1. Prerequisites, 2. Installation, 3. Running the `pump` library, 4. Running the `pumpflow` desktop app, 5. Testing, 6. Troubleshooting, 7. Quick reference, A first end-to-end run (+13 more)

### Community 55 - "theme.py"
Cohesion: 0.06
Nodes (36): _colors(), contrast(), family(), font_px(), length(), _lengths(), _luminance(), pump.design ===========  The PumpFlow design system in code: :file:`tokens.json` (+28 more)

### Community 56 - "Spec-Driven Software Engineering: Adapting the CentrifugalPump Project to the OpenSpec Methodology"
Cohesion: 0.10
Nodes (19): 1.1 Specification-by-Example (SBE) and Behavior-Driven Development (BDD), 1.2 Living Documentation, 1.3 Traceability and Change Proposals, 1. Theoretical Fundamentals of OpenSpec, 2.1 Technical and Strategic Alignment, 2.2 Decision Matrix, 2. Evaluation: Should You Implement This?, 3.1 Step-by-Step "How" Guide (+11 more)

### Community 57 - "LatexReportGenerator"
Cohesion: 0.14
Nodes (14): NPSHrCurve, plot_npsh(), BytesIO, ndarray, Q_, Least-squares polynomial of NPSHr versus capacity.      Parameters     ---------, NPSHr (metres) at capacity ``q`` from the fitted polynomial., NPSHr at the rated capacity. (+6 more)

### Community 58 - "test_persistence_roundtrip.py"
Cohesion: 0.27
Nodes (3): EdgeItem, QPointF, QGraphicsPathItem

### Community 59 - "test_report_formats.py"
Cohesion: 0.11
Nodes (20): npsh_available(), NPSH available at the pump suction, in metres.      ``NPSHa = (p_s,abs - p_v) /, Pressure, Any, Serialise to ``{"value", "unit", "ref", "atm": {"value", "unit"}}``.          Ex, Rebuild from :meth:`to_json` output (``ref`` defaults to gauge, ``atm``, A pressure value together with its reference.      Parameters     ----------, npsha_from_suction() (+12 more)

### Community 60 - "RUN_AND_TEST.md"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h), Tasks (≈ 8 h)

### Community 61 - "CLAUDE.md"
Cohesion: 0.13
Nodes (14): Acceptance: one engine ([pump/acceptance.py](pump/acceptance.py), ADR 0012), Architecture: the `pump` library, Architecture: the `pumpflow` workbench, Common commands, Conventions and gotchas, Curves and transforms ([pump/performance_curve.py](pump/performance_curve.py)), Domain model, graphify (+6 more)

### Community 62 - "README.md"
Cohesion: 0.19
Nodes (6): Sprint index, Sprint template, Sprints, Contents, Guidelines, Use-case worked examples

### Community 63 - "PerformanceCurve"
Cohesion: 0.18
Nodes (6): BasePoint, Returns a detailed string representation of the fluid's properties., Represents a system point with physical quantities.      Parameters     --------, Returns a detailed string representation of the fluid's properties., Returns a detailed string with fluid's properties., Returns a detailed string representation of the fluid's properties.

### Community 64 - "ExploreChartNode"
Cohesion: 0.09
Nodes (22): Formula explanations for the workbench (UC-10, educational mode).  One dictionar, Tooltip text ``"<title>\\n<text>"`` for ``key``.      Raises     ------     KeyE, tooltip(), _blank_rows(), calc_npsha(), _m(), NPSHNode, overrides_to_quantities() (+14 more)

### Community 65 - "QLabel"
Cohesion: 0.29
Nodes (6): QWidget, A spacing token of the design system, in pixels., Like row() but with a QComboBox as the suffix widget for unit selection., row(), _sp(), unit_row()

### Community 66 - "ARCHITECTURE.md"
Cohesion: 0.08
Nodes (25): Exception, BindingError, make_fluid(), Human-readable wrapper around library/validation failures (UI_SPEC §7)., Construct a ``pump.Fluid`` (or ``Water``) from a Fluid-node spec (UC-00)., make_system_curve(), Q_, rated_from_candidate() (+17 more)

### Community 67 - "Build & Development Guide"
Cohesion: 0.15
Nodes (12): 1. Prerequisites, 2. Environment Setup, 3. Running the Applications, 4. Code Quality & Testing, 5. Building Documentation, 6. Creating a Distributable Package, Build & Development Guide, Formatting (+4 more)

### Community 68 - "NodeItem"
Cohesion: 0.27
Nodes (11): _fitted(), _rated(), Qt (offscreen) tests: Impeller Trim node, rated-point diameters, codec (sprint 1, test_rated_point_carries_impeller_diameters(), test_trim_dialog_opens(), test_trim_node_accepts_corrected_curve_input(), test_trim_node_default_idle_without_inputs(), test_trim_node_duty_mode_and_binding() (+3 more)

### Community 69 - "PortItem"
Cohesion: 0.05
Nodes (42): DesignPoint, Q_, Specific energy is the energy per unit mass of fluid.         It is calculated a, The mechanical power transferred to the liquid as it passes through the pump,, Calculates the outlet pressure based on inlet pressure and various heads., Calculates the head difference due to elevation.          Returns         ------, Calculates the fluid velocity at the pump inlet.          Returns         ------, Calculates the fluid velocity at the pump outlet.          Returns         ----- (+34 more)

### Community 70 - "Dev Journey — your map when it feels like too much"
Cohesion: 0.17
Nodes (12): 2026-10-27, A use case is "in production" when…, Dev Journey — your map when it feels like too much, Latest Work Log, Read this when you're overwhelmed, The next sprints (sequenced for you), The one rule, The second rule — structure by domain, steer by use cases (+4 more)

### Community 71 - "test_pump_smoke.py"
Cohesion: 0.07
Nodes (48): Channel, ChannelResult, MechanicalRunChecker, MechanicalRunCriteria, MechanicalRunLog, MechanicalRunResult, _parse_quantity(), _parse_time() (+40 more)

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
Cohesion: 0.13
Nodes (21): export_test_summary(), Write the summaries; ``(paths, errors)`` like :func:`export_reports`., build_scene(), main(), Headless report export: ``.pumpflow`` project → Word / LaTeX / PDF / HTML.  Usag, Load ``project`` into an evaluated :class:`GraphScene` (offscreen Qt)., ``(rated, branches, settings)`` from the project's Report Export node., Settings of every Markdown Note node (those tagged ``report`` feed the report). (+13 more)

### Community 77 - "scene.py"
Cohesion: 0.11
Nodes (33): make_design_point(), Construct the shared ``DesignPoint`` (UI_SPEC §4)., assemble_report_data(), build_report_png(), cover_from_settings(), generate_html(), open_points_from_notes(), pumpflow.binding.reports  Report data assembly and export (docx, tex, pdf, html) (+25 more)

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
Cohesion: 0.15
Nodes (11): Path, QDialog, QFrame, QWidget, Splash / start-screen modal shown over the main window at launch.      The calle, Build the left column listing the most recently opened projects.          Notes, Build the right column listing bundled example pipelines.          Only examples, Load a project from *path* and accept the dialog.          Parameters         -- (+3 more)

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
Cohesion: 0.33
Nodes (6): Back-compatibility, Extending it, How it is wired, Multi-unit handling — design philosophy, Pint end to end (001_masterpiece), The invariants

### Community 93 - "Audience"
Cohesion: 0.33
Nodes (6): Audience, Primary — Performance test / FAT engineer, Repo-vs-spec discrepancy, Roles explicitly out of scope, Secondary — Application / selection engineer *(pending owner sign-off)*, Tertiary — Student / learner *(pending owner sign-off)*

### Community 94 - "Sprint S1 — Test foundation + units spec (8 h)"
Cohesion: 0.14
Nodes (26): PerformanceLine, One vibration row: ``(tested, specified)`` in mm/s RMS for each region., One row of the hydraulic block (values in ``unit``; deviation a fraction)., VibrationLine, limit_group(), Which limit table applies: ``"vs"`` (Table 9 / 2-6) or ``"oh_bb"`` (Table 8 / 2-, Bearing-housing vibration limits for the rated pump (``limits`` dict).      The, vibration_limits_for() (+18 more)

### Community 95 - "Sprint S2 — Pin the MVP physics (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S2 — Pin the MVP physics (8 h), Tasks (≈ 8 h)

### Community 96 - "Sprint S3 — GUI-openable case + persistence guard (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S3 — GUI-openable case + persistence guard (8 h), Tasks (≈ 8 h)

### Community 97 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.11
Nodes (25): compare_curves(), ComparisonRow, ComparisonTable, plot_comparison(), Q_, Relative delta ``(value - ref) / ref`` (NaN when the reference is zero)., Compare fitted curves at the given capacities.      Parameters     ----------, Overlay head, power and efficiency of several curves (three stacked panels). (+17 more)

### Community 98 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.15
Nodes (16): fit_model(), Polynomial coeffs (primary) + natural cubic splines (secondary)., CorrectedCurve, A ``pump.PerformanceCurve`` corrected to rated speed + rated fluid., fitted(), test_export_pumpcurve_binding_round_trip(), _fitted(), Qt (offscreen) tests: System Curve + Operating Point nodes (sprint 11 / UC-03, U (+8 more)

### Community 99 - ".__init__"
Cohesion: 0.09
Nodes (8): canvas.node_item ================  The on-canvas representation of one workflow, BaseNode, Plain-JSON view of ``settings`` for ``.pumpflow`` (override if needed)., Return ``{output_port_name: payload}``.  Override me., Return a configured ``QDialog`` (or ``None`` if the node has none)., Set the canvas verdict pill (tone ``ok`` / ``fail`` / ``warn``)., Helper: clear outputs and show an amber/idle status (UI_SPEC §7)., ComplianceCheckNode

### Community 100 - "PumpLab — Documentation"
Cohesion: 0.10
Nodes (29): Load an edition, optionally merged with a client overlay.          The overlay r, The default criteria (``api610:12``, no client overlay)., Edition-aware acceptance criteria (Sprint 5) — Qt-free.  Covers the TOML-backed, test_10th_edition_stays_unverified(), test_api610_8th_table_4_2(), test_checked_editions_cite_their_clauses(), test_default_is_api610_12(), test_default_tolerances_match_table_16() (+21 more)

### Community 101 - "RatedPointInputNode"
Cohesion: 0.21
Nodes (22): η = hydraulic / breaking, in percent.  ``ρ`` is water at ``T_water`` by     defa, Read-only ``Head`` column for the Test Points grid (UI_SPEC §5.2):     ``Head =, row_efficiency(), row_head(), One raw measured row of a FAT performance test., TestRow, _g(), _rated() (+14 more)

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
Cohesion: 0.23
Nodes (12): npsh3_from_sweep(), NPSH3 from a suction sweep at one flow.      The sweep is a series of decreasing, _b34004a_curve(), _hand_npsha(), NPSH margin (UC-05): NPSHa, NPSH3 sweep, NPSHr curve, margin / check, the legacy, test_margin_and_ratio(), test_npsh3_sweep_known_knee(), test_npsh3_sweep_never_drops() (+4 more)

### Community 108 - ".to_fluid"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 14 — Masterpiece polish: report, CI, docs, Tests

### Community 109 - "run"
Cohesion: 0.21
Nodes (12): overall_verdict_text(), Consolidated verdict of several pumps, in the Compliance node's words.      REJE, ComplianceResult, Per-parameter verdicts + the per-pump overall verdict., The verdict as every view shows it (canvas, Compliance, Report Export)., _approved(), _partial(), _rejected() (+4 more)

### Community 111 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.17
Nodes (12): 1 · Before test day: read the datasheet like an inspector, 2 · Which tolerance applies, 3 · Efficiency is not a pass/fail item (usually), 4 · Shut-off head and the rising curve, 5 · NPSH: two separate rules, 6 · Vibration: RMS only, 7 · The mechanical run, 8 · The test data summary (Annex M / 8th App. T) (+4 more)

### Community 112 - "ADR 0005 — Consolidate the `Point` hierarchy & remove broken code"
Cohesion: 0.50
Nodes (4): ADR 0005 — Consolidate the `Point` hierarchy & remove broken code, Consequences, Context, Decision

### Community 113 - "ADR 0006 — Replace `hasattr` duck-typing with an explicit schema"
Cohesion: 0.30
Nodes (15): code(), main(), md(), Generate the worked use-case notebooks of sprint 13.  Every notebook is written, tr01(), uc01(), uc02(), uc0304() (+7 more)

### Community 114 - "ADR 0007 — Remove the ACL leak: private-attribute pinning in `binding`"
Cohesion: 0.30
Nodes (10): Fit ``H_static`` and ``k`` through two ``(q, h)`` points.          Examples, ``H(Q) = static_head + k * Q**exponent``.      Parameters     ----------     sta, SystemCurve, System curve (UC-03): H = H_static + k·Q^n, two-point fit, Darcy–Weisbach pipe., test_curve_returns_quantity_array(), test_from_points_other_exponent(), test_from_points_recovers_k(), test_head_static_plus_k() (+2 more)

### Community 115 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.13
Nodes (15): Educational layer, MVP use cases, Priority summary, UC-00 — Work in the engineer's own measurement units ✅, UC-01 — Select a pump for given conditions ✅, UC-02 — Verify pump performance (FAT) ✅, UC-03 / UC-04 — System curve and operating point ✅, UC-05 — Check NPSH margin ✅ (+7 more)

### Community 116 - "ADR 0010 — Align versioning & declare GUI dependencies"
Cohesion: 0.50
Nodes (4): ADR 0010 — Align versioning & declare GUI dependencies, Consequences, Context, Decision

### Community 118 - "hline"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 2 — Signals carry Quantities + `.pumpflow` schema v2, Tests

### Community 119 - "int_spin"
Cohesion: 0.11
Nodes (24): make_node(), Node windows: maximise from the title bar, a header Maximize / Restore button on, test_button_and_double_click_toggle(), test_chart_windows_have_header_button(), test_every_node_window_has_min_max_buttons(), test_short_forms_have_no_header_button(), test_size_and_maximised_state_remembered(), test_default_dialog_opens() (+16 more)

### Community 120 - "line_edit"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 4 — Complete head (pressure + velocity + elevation), Tests

### Community 137 - "pumpflow/binding.py"
Cohesion: 0.16
Nodes (10): _opt(), _p_label(), PointNode, Return a positive float, or ``None`` when blank/zero/non-numeric., ``_opt``, normalise to the standard unit and wrap as a Quantity in     ``out_uni, The stored pressure display label, tolerating legacy Pint-string values., Derive head (m) from suction/discharge pressures + fluid density., _std_opt() (+2 more)

### Community 150 - "pumpflow/binding.py"
Cohesion: 0.36
Nodes (3): BeforeAfterTable, Read-only before/after table (Q, Head, Power, η, stage) with display-unit     co, Show ``({"measured": row, "corrected": row}, ...)`` pairs.

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
Cohesion: 0.16
Nodes (17): find_latex_engine(), Return the command used to build a PDF, or ``None`` when no TeX is found., _mm_s(), Q_, Maximum vibration per probe and flow region, tested vs specified.      Parameter, vibration_by_region(), _pts(), API 610 test data summary (Annex M / 8th-edition Appendix T). (+9 more)

### Community 172 - "Banner"
Cohesion: 0.12
Nodes (15): _btn(), _bundle_json(), _mag(), _pick_dir(), _pick_file(), nodes.report_export — Report Export  (UI_SPEC §5.7)  Inputs: the shared ``RatedP, Fill the cover keys a project saved before sprint 14 does not carry., Settings of the Markdown Note nodes on the same canvas (may be empty). (+7 more)

### Community 173 - "NaturalCubicSpline"
Cohesion: 0.23
Nodes (11): _node(), Qt (offscreen) tests: Pump Selection node + dialog (sprint 12 / UC-01)., test_choice_selects_another_row(), test_default_instance_evaluates_without_a_catalogue(), test_empty_folder_is_idle(), test_gpm_ft_duty_gives_the_same_result(), test_no_pump_fits_is_invalid(), test_non_positive_duty_is_invalid() (+3 more)

### Community 174 - ".__init__"
Cohesion: 0.29
Nodes (7): QPointF, QRectF, A filled dot carrying a glyph (✓ ! ✗); idle is a hollow ring., Draw a rounded verdict pill at ``x`` (or centred); return its right edge., Zoomed out: the body shows only the verdict (or a large state glyph)., port_color(), QColor

### Community 175 - "001_masterpiece — Loop Protocol"
Cohesion: 0.10
Nodes (15): Add the NPSH section (UC-05).          Parameters         ----------         doc, Add the pump comparison section (UC-08).          Parameters         ----------, Generates a report from predefined templates using the `python-docx` library., Retrieve the appropriate template file based on the selected language., Generates a report from a predefined template.          Parameters         -----, Add the cover block (title + project / client / tags / standard / date /, Add "Deviations and open points" (unverified criteria + open points)., Add the signature table (Role / Name / Signature / Date). (+7 more)

### Community 176 - ".paint"
Cohesion: 0.16
Nodes (8): _axis_scale(), ExploreChartNode, _mag(), Pin every left axis to the widest one so the plot frames (and the         shared, A capacity field (any capacity unit) + a table of the values each         fitted, A vertical guide + value label that follows the cursor across panes., Magnitude of an optional Quantity in ``unit`` (``None`` stays ``None``)., ``(scale, display_unit)`` mapping canonical axis values to the preset's     disp

### Community 177 - "hline"
Cohesion: 0.17
Nodes (6): Smoke / regression tests for the ``pump`` engineering library.  These are intent, test_checker_head_tolerance_band(), test_checker_shutoff_tolerance_tier(), test_quantity_factory_canonicalizes_capacity(), test_quantity_factory_rejects_non_quantity(), test_report_summary_keys()

### Community 178 - ".to_speed"
Cohesion: 0.50
Nodes (3): Shared rated point/fluid + one entry per pump TAG, ready to serialize., Acceptance reflects ALL pumps (UI_SPEC §2 / §9)., ReportBundle

### Community 179 - ".__getitem__"
Cohesion: 0.13
Nodes (9): The unit combo of a ``ui.PressureField`` (tolerant of its internals)., _unit_combo(), combo(), A unit-aware numeric field: a spinbox + a display-unit combo that     auto-conve, Programmatically switch the display unit (converts the shown value)., spin(), UnitField, QComboBox (+1 more)

### Community 180 - ".import_data_file"
Cohesion: 0.12
Nodes (8): Library quantity spine — sprint 1 of project 001_masterpiece.  Asserts the new s, test_cst_quantity_factory_emits_no_warning(), test_stokes_converts_to_cst(), test_water_100c_vapour_pressure(), test_water_20c_kinematic_viscosity(), test_water_20c_vapour_pressure(), test_water_equality_and_dict_unaffected_by_new_properties(), test_water_vapour_pressure_out_of_range_raises()

### Community 181 - ".__len__"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 10 — UC-07 Impeller trim, Tests

### Community 182 - ".__repr__"
Cohesion: 0.14
Nodes (22): _b34004a_log_settings(), _b34004a_settings(), _check(), _node(), Qt (offscreen) tests: MRT Log + MRT Check nodes, codec round-trip, the legacy on, An MRT Check fed by ``log_node``: ``(check node, outputs)``., MRT Log follows the Test Points layout: one unit combo above each     channel co, A witness-day template with times but no values must be invalid (no     verdict, (+14 more)

### Community 183 - "checkbox"
Cohesion: 0.17
Nodes (8): PropertyDialog, QDialog, Maximise the window, or restore it to its previous size., Restore the last size / maximised state saved under ``key`` and save         it, Resize the window to fit header + body preferred size (opt-in).          Used by, Where node windows remember their size (app settings, not the project).      Tes, A consistent shell: header, a body you fill, and live-apply semantics.      Ever, window_settings()

### Community 184 - "export_cli.py"
Cohesion: 0.20
Nodes (26): _construction_rows(), _dev(), _header_rows(), _num(), _perf_header(), _perf_rows(), Path, Translate (+18 more)

### Community 185 - "PerformancePlotNode"
Cohesion: 0.32
Nodes (3): PerformancePlotNode, BytesIO, Y-limits converted from their display unit to canonical m / kW / %.

### Community 186 - ".absolute"
Cohesion: 0.09
Nodes (27): _fmt(), _latex_char(), latex_escape(), LatexReportGenerator, Path, One character for pdflatex: escaped, mapped, or a visible placeholder.      Char, Escape LaTeX special characters in ``text`` (converted with ``str``).      Also, Same number formatting as the docx report (``0.02f~P`` for quantities). (+19 more)

### Community 187 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.20
Nodes (5): CheckRow, PerformanceVerdict, One acceptance check at the rated point.      ``status`` is ``"pass"``, ``"fail", True for rows that take part in the verdict., Outcome of :func:`evaluate_performance`.      ``passed`` means no judged row fai

### Community 188 - "TestPointsTableNode"
Cohesion: 0.14
Nodes (4): Qt-free tests for the multi-unit spine: UNIT_OPTIONS, header parsing, codec., test_codec_decode_unlabelled_columns_go_canonical(), test_codec_roundtrip_test_points_columns(), _tp_runtime()

### Community 189 - "Data Formats"
Cohesion: 0.08
Nodes (40): utilities =========  This submodule provides unit conversion utilities to standa, comparison_sentence(), comparison_table(), cover_rows(), deviation_items(), Self-contained HTML report generation.  Consumes the **same** ``report_data`` di, LaTeX (``.tex``) and PDF report generation.  Consumes the **same** ``report_data, mechanical_run_duration_sentence() (+32 more)

### Community 190 - "line_edit"
Cohesion: 0.19
Nodes (9): Path, Clear the unsaved-changes flag.          Removes the asterisk appended by :meth:, Replace the canvas with *doc* and update session state.          Parameters, Serialise the canvas to the current ``.pumpflow`` file (File > Save).          F, Serialise the canvas to a chosen ``.pumpflow`` path (File > Save As)., Load a ``.pumpflow`` project file into the canvas (File > Open).          Guards, write_json(), Prepend *path* to the persisted recent-files list.      Deduplicates and caps th (+1 more)

### Community 191 - "SystemCurveNode"
Cohesion: 0.23
Nodes (11): The status line without the segment the verdict pill already shows.      ``"B-1A, _status_beside(), _logic(), Qt (offscreen): the canvas verdict pill and first-open dialog sizing (UI/UX revi, scene(), test_badge_cleared_when_node_loses_input(), test_first_open_fits_table_headers(), test_judging_nodes_carry_a_badge() (+3 more)

### Community 192 - ".is_empty"
Cohesion: 0.14
Nodes (12): LocalizationHelper, _parse_po(), One sentence listing user-overridden tolerances, or ``""`` when none.      ``ove, Minimal ``.po`` reader: ``{msgid: msgstr}`` for non-empty translations.      Han, Handles translation and localization using gettext.      Parameters     --------, Sets up gettext for localization.          Returns         -------         Calla, tolerance_override_sentence(), test_new_headings_translated_to_portuguese() (+4 more)

### Community 193 - ".density_rel"
Cohesion: 0.08
Nodes (22): _dimensionless(), _kinematic_viscosity(), PerformanceCurve, Any, Q_, Generates a report summarizing predicted performance values.                  Re, A container for handling a collection of TestPoint objects that share the same f, Predicts the head for a given flow (capacity) using the stored polynomial. (+14 more)

### Community 194 - "._mark_clean"
Cohesion: 0.22
Nodes (8): Acceptance, Assumes, Definition of done, Files, Goal, Reuse, Sprint 13 — UC-10 Educational mode + a worked notebook per use case, Tests

### Community 195 - "UnitPrefs"
Cohesion: 0.25
Nodes (4): canonical_unit(), The library's standard display label for a dimension (first option)., Holds the active project-level unit preset (SI / US / custom).      ``default_un, UnitPrefs

### Community 196 - "Pressures"
Cohesion: 0.30
Nodes (10): _col(), _head(), _header(), Qt (offscreen) tests: per-column units on the Test Points table., _select(), _setup(), test_capacity_roundtrip_restores_values_and_head(), test_paste_with_headers_sets_units() (+2 more)

### Community 197 - "correct_curve"
Cohesion: 0.24
Nodes (6): ADR 0011 — Schema v2: value + unit persistence, Alternatives considered, Consequences, Context, Decision, 001_masterpiece — Pint end to end, every use case, FAT-grade acceptance

### Community 199 - ".__init__"
Cohesion: 0.24
Nodes (5): ``(minus, plus)`` shut-off tolerance: criteria band or user override., Computes the acceptable limits for head, shutoff head, and breaking power., Initializes the PerformanceChecker with a design point and performance curve., Determines the shutoff head tolerance (plus side) from the rated         differe, ``(minus, plus)`` head tolerance: criteria band or user override.

### Community 200 - "check_npsh_set"
Cohesion: 0.12
Nodes (20): pump_family(), ``"OH"``, ``"OH_VIL"``, ``"OH6"``, ``"BB"`` or ``"VS"`` (``None`` if unknown)., check_mechanical_run(), check_npsh_set(), criteria_label(), pumpflow.binding.acceptance  Acceptance criteria and the Compliance, NPSH and me, Check a mechanical-run log against the acceptance criteria.      The criteria co, Judge a pump's NPSH margin: NPSHa against the NPSHr curve at rated Q.      The c (+12 more)

### Community 201 - "Data Formats"
Cohesion: 0.18
Nodes (10): grouped_node_kinds(), ``NODE_KINDS`` split into :data:`NODE_GROUPS`; any kind not listed goes     into, Two-line label of a recent project: file name, then folder · modified date., recent_label(), UI/UX review, round 2 (2026-11-18): disabled fields read as disabled, a tick in, test_every_node_is_in_exactly_one_named_group(), test_geometry_rows_disabled_until_applied(), test_rated_point_cover_label_is_named() (+2 more)

### Community 202 - ".available"
Cohesion: 0.25
Nodes (7): API, Assumptions, NPSH, NPSH available, NPSH required, NPSH3 and the margin, Two different rules, Worked notebook

### Community 203 - "_fmt_value"
Cohesion: 0.12
Nodes (18): Return the canonical single-pump ``.pumpflow`` document (Qt-free, schema v2)., sample_project_doc(), b34004_scene(), _build_scene(), ``.pumpflow`` persistence guard — UC-02 / UC-09 (the workbench demo case).  Two, Open every node's property dialog: on the B-34004 project (branch B has     no f, Sprint 10: diameter that puts B-34004A on its rated point lies inside the     da, A template row with no N / P / ΔP must be rejected by validation; before     the (+10 more)

### Community 204 - "test_compliance_gui.py"
Cohesion: 0.25
Nodes (4): _curve(), Minimal curve: H = 357 - 0.18 Q^2 (m, m3/h); power and efficiency fixed., test_f02_extrapolated_note_when_no_q0_point(), test_shutoff_extrapolated_without_low_flow_point()

### Community 205 - "Pressures"
Cohesion: 0.18
Nodes (8): Limits, RMS, peak and the vendor's word, The high-speed chart (11th ed. Figure 34, 12th ed. Figure 35), Vibration: by pump type, and the high-speed chart, Where to measure depends on the pump type, Before you start, Sources, Training

### Community 206 - ".absolute"
Cohesion: 0.50
Nodes (4): ADR 0001 — Establish an automated test harness, Consequences, Context, Decision

### Community 207 - "ADR 0002 — Fix the `pint` `NameError` in the units foundation"
Cohesion: 0.50
Nodes (4): ADR 0002 — Fix the `pint` `NameError` in the units foundation, Consequences, Context, Decision

### Community 208 - "parse_standard_text"
Cohesion: 0.25
Nodes (4): _high_speed(), Bearing-housing vibration limits (RMS, preferred operating region) by pump     f, ``{"overall": Q_, "filtered": Q_, "basis": str}`` for a pump type         (OH/BB, VibrationCriteria

### Community 209 - "Sprint S4 — Docstrings & doctests (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S4 — Docstrings & doctests (8 h), Tasks (≈ 8 h)

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
Cohesion: 0.29
Nodes (5): Qt (offscreen) test: criteria-aware compliance on the B-34004A reference project, _results(), scene(), test_project_evaluates_with_criteria_metadata(), test_reset_restores_criteria_defaults()

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
Cohesion: 0.33
Nodes (6): Capabilities at a glance, Documentation map, Project layout, PumpLab — Documentation, Quick start, The seven widgets

### Community 221 - "Banner"
Cohesion: 0.07
Nodes (18): available_clients(), available_standards(), ``[(key, label)]`` of the editions the library offers., ``[(client, label)]`` of the client overlays the library offers., _append_param(), _Fallback, QTableWidget, Stand-in rated point for the tolerance dialog before a RatedPoint is wired. (+10 more)

### Community 222 - "YLimDisp"
Cohesion: 0.20
Nodes (9): curve(), design_point(), _dispose_graph_scenes(), Shared pytest fixtures for the ``pump`` library suite.  These were originally in, Cold water at ~997 kg/m³ — the reference fluid for the suite., A small, monotonic Q×H / Q×P performance curve at 1750 rpm., Rated/design point matching the curve's rated region (833 m³/h, 73 m)., Hand canvas items back to Python before their scenes are discarded.      Without (+1 more)

### Community 224 - "UnitColumnHeader"
Cohesion: 0.20
Nodes (5): Guard destructive actions with a Save / Discard / Cancel prompt.          Presen, Create a blank canvas (File > New).          Prompts to save unsaved changes bef, Intercept the window close event to guard unsaved work.          Parameters, Display the start-screen dialog and act on the user's choice.          Called on, Frame the whole pipeline (zoom extents).

### Community 225 - "_bundle_json"
Cohesion: 0.08
Nodes (35): Location, location_of_key(), locations_for(), pump.vibration ==============  API 610 pump types and where their bearing-housin, Measurement locations of a pump type (drive end / non-drive end if unset)., Column keys (overall, filtered) for every location of a pump type., ``(Location, filtered)`` of a column key such as ``vib_gb_f``.      Raises     -, A bearing-housing measurement location of a pump type. (+27 more)

### Community 227 - "RunLog"
Cohesion: 0.39
Nodes (6): _heads(), _logic(), Qt (offscreen) test: Test Points node with bench geometry (sprint 4)., test_dialog_head_column_tooltip_lists_components(), test_geometry_shifts_head_by_velocity_plus_elevation(), test_unset_geometry_emits_none()

### Community 228 - "Affinity laws"
Cohesion: 0.29
Nodes (6): Affinity laws, API, Assumptions, Finding the speed or diameter for a duty, The laws, Worked notebooks

### Community 229 - "SelectionCriteria"
Cohesion: 0.29
Nodes (6): Changing the look, Contrast fixes made when the system was formalised (2026-11-17), Design system, Rules, The artifact, The families

### Community 230 - "SystemCurveNode"
Cohesion: 0.11
Nodes (17): Replace ``@token`` and ``@fs-<style>`` placeholders in ``template``.      Colour, render(), MarkdownNoteNode, info_button(), A small round "i" button that opens ``html`` in a modeless help box., A section heading followed by an :func:`info_button`., section(), section_with_info() (+9 more)

### Community 231 - "Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)"
Cohesion: 0.40
Nodes (5): 001_masterpiece — Loop Protocol, Changelog, Open items needing owner input, Standing rules (every sprint), Tracker

### Community 232 - "001_masterpiece — Loop Protocol"
Cohesion: 0.14
Nodes (16): constants =========  Physical constants shared by the whole library, as Pint qua, check_npsh(), npsh_margin(), NPSHCriteria, NPSHResult, npsh ====  Net Positive Suction Head (NPSH) tools for the Performance test (UC-0, Ratio ``NPSHa / NPSHr`` and margin ``NPSHa - NPSHr``.      Examples     --------, NPSH margin rule.  Seeded as *not configured*: both limits are ``None``.      At (+8 more)

### Community 233 - "NPSHNode"
Cohesion: 0.25
Nodes (4): A strip of unit combos laid out above a ``QTableWidget``'s columns., A unit combo for one table column (or ``span`` adjacent columns).      ``on_chan, UnitColumnHeader, UnitHeaderStrip

### Community 234 - "ADR 0009 — Promote `mathx` into the `pump` library"
Cohesion: 0.50
Nodes (4): ADR 0009 — Promote `mathx` into the `pump` library, Consequences, Context, Decision

### Community 235 - "Data Formats"
Cohesion: 0.18
Nodes (9): 60-second orientation, CentrifugalPump — Documentation, Deeper references (pumpflow UI), Start here, 1 · Data-exchange JSON (UI_SPEC §6.2), 2 · Project file — `.pumpflow` (UI_SPEC §6.1), 3 · Report outputs, Data Formats (+1 more)

### Community 236 - "Banner"
Cohesion: 0.24
Nodes (6): _length_opt(), _opt(), RatedPointInputNode, An optional length setting as a Quantity in mm (``None`` when unset/<= 0)., ``(standard_key, client)`` of the settings: stored keys, else parsed text., _standard_keys()

### Community 237 - ".deviation"
Cohesion: 0.10
Nodes (24): _band(), _band_for(), deviation(), evaluate_performance(), head_rises_to_shutoff(), _limit(), _merge_sub(), _parse_bands() (+16 more)

### Community 239 - "YLimDisp"
Cohesion: 0.27
Nodes (6): _label_or_canonical(), _q_dec(), ``(label, converted?)`` for a stored unit: its label, else canonical., On-disk ``{"value", "unit"}`` -> runtime ``{"value", "unit": label}``., Mechanical-run settings: channel units and criteria overrides.      ``columns``, RunLog

### Community 240 - "CentrifugalPump — Documentation"
Cohesion: 0.20
Nodes (7): NPSHTable, parse_standard_text(), NPSH-node settings: per-column units of the NPSHr table + the margin override., ``(standard_key, client)`` from the free-text rated-point ``standard``.      ``", Normalise a v1 runtime-shaped settings dict before :func:`encode`.      Missing, upgrade_v1(), test_parse_standard_text()

### Community 241 - "_bundle_json"
Cohesion: 0.25
Nodes (7): ABC, ImprovedQuantity, Q_, Defines an abstract interface for unit conversion.          Methods     -------, Implements unit conversion based on predefined standard units., Converts a given quantity to its corresponding standard unit.          Parameter, UnitConverterInterface

### Community 242 - "TestRow"
Cohesion: 0.22
Nodes (8): 1. Findings index, 3. Next-generation options, 4. Suggested first sprint (if Option A is accepted), Code Review — Toward the Next-Generation Tool, Option A — Harden the core (recommended first), Option B — Headless-first FAT pipeline (`pump-cli`), Option C — Physics expansion (parallel track), Option D — Web workbench

### Community 243 - "QSettings"
Cohesion: 0.25
Nodes (7): load_recent(), welcome =======  Start-screen dialog shown on application launch.  Presents Rece, Return the persisted recent-file paths, skipping any that no longer exist., QSettings, no_saved_geometry(), isolated_settings(), Point the window memory at a throw-away INI file.

### Community 244 - "Disp"
Cohesion: 0.22
Nodes (4): Disp, OptDisp, Value with a runtime display label: ``key`` + ``unit_key`` <-> quantity., Optional :class:`Disp`: an unset (``None``) value is **omitted** on disk.      T

### Community 245 - "Acceptance tolerances (data-driven)"
Cohesion: 0.25
Nodes (7): Acceptance tolerances (data-driven), Client overlay: Petrobras N-553 rev E, How it is wired, One engine, three outcomes, The values, by edition, The `verified` flag, What is checked

### Community 246 - ".verdict"
Cohesion: 0.25
Nodes (5): _fmt_value(), The :class:`pump.acceptance.PerformanceVerdict` of this design point.          T, Parallel-operation rule: shut-off head / rated differential head         >= ``pa, Table of the rated-point checks (not of every raw test point), from         :met, Format a table cell: Pint quantities with ``0.02f~P``, others as text.

### Community 247 - ".import_data_file"
Cohesion: 0.32
Nodes (3): _mag_or(), Wire a Pump B branch to the same Rated Point + Report (UI_SPEC §2 A/B)., Magnitude of an optional Quantity in ``unit``, or ``default`` when ``None``.

### Community 248 - ".absolute"
Cohesion: 0.29
Nodes (4): Q_, Difference of two pressures (reference-free), in the units of ``self``., Absolute pressure, in the units of ``value``.          Examples         --------, Gauge pressure, in the units of ``value``.          Examples         --------

### Community 249 - "Pressures"
Cohesion: 0.38
Nodes (3): _atm(), Pressures, Pressures sharing one runtime unit label + g/a reference -> ``{value, unit, ref}

### Community 250 - "_disk_unit"
Cohesion: 0.33
Nodes (6): _disk_unit(), _fmt(), _q_enc(), The unit string written to disk for a display label.      Compact Pint spelling, Runtime ``{"value", "unit": label}`` -> on-disk ``{"value", "unit": pint}``., Compact (``~C``) Pint spelling, as produced by ``pump.quantity_io.to_json``.

### Community 251 - "_pint"
Cohesion: 0.29
Nodes (4): _pint(), Pint string of a display label (a bare Pint string is accepted too)., Optional ``[lo, hi]`` axis limits with a runtime unit label., YLimDisp

### Community 252 - "Sprint S1 — Test foundation + units spec (8 h)"
Cohesion: 0.33
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S1 — Test foundation + units spec (8 h), Tasks (≈ 8 h)

### Community 253 - ".showEvent"
Cohesion: 0.33
Nodes (4): fit_table_headers(), On the first show, make table headers readable and, unless a size         was re, Size the window to its content: full width, height capped at 85 % of         the, Give every table under ``root`` room for its full column headers.      Tables st

### Community 254 - "Sprint S0 — Product context & sprint scaffold (8 h)"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S0 — Product context & sprint scaffold (8 h), Tasks (≈ 8 h)

### Community 255 - "Sprint S6 — Repo README + wrap (8 h)"
Cohesion: 0.40
Nodes (5): Acceptance criteria, Definition of Done, Files touched, Sprint S6 — Repo README + wrap (8 h), Tasks (≈ 8 h)

### Community 256 - "export_pumpcurve"
Cohesion: 0.50
Nodes (4): main(), Build the example pump catalogue (``*.pumpcurve.json``) from the shipped project, export_pumpcurve(), Write a fitted curve as a catalogue file (``*.pumpcurve.json``).      The entry

### Community 257 - ".from_table"
Cohesion: 0.40
Nodes (4): _parse_quantity(), Build from a TOML ``npsh`` table (missing limits stay ``None``)., Parse ``"1 m"`` into a Pint quantity., test_criteria_from_table()

### Community 259 - "ADR 0012 — One performance-verdict engine, no silent passes"
Cohesion: 0.50
Nodes (4): ADR 0012 — One performance-verdict engine, no silent passes, Consequences, Context, Decision

## Knowledge Gaps
- **554 isolated node(s):** `centrifugal-pump`, `Fast Orientation`, `Commands (Match Repo Config)`, `Testing Gotchas`, `Hard Boundary` (+549 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **68 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `make_node()` connect `int_spin` to `registry.py`, `MainWindow`, `PerformancePlotNode`, `curve_fit.py`, `Data Formats`, `NaturalCubicSpline`, `.__repr__`, `SystemCurveNode`, `NodeItem`, `Pressures`, `check_npsh_set`, `EdgeItem`, `Data Formats`, `_fmt_value`, `Node & Banner State Colors`, `upgrade_v1`, `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `.__init__`, `RunLog`, `Sprint S0 — Product context & sprint scaffold (8 h)`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `GraphScene` connect `GraphScene` to `RunLog`, `Pressures`, `MainWindow`, `curve_fit.py`, `EdgeItem`, `SpeedCorrectionNode`, `Sprint S0 — Product context & sprint scaffold (8 h)`, `Node & Banner State Colors`, `_fmt_value`, `.__repr__`, `upgrade_v1`, `test_persistence_roundtrip.py`, `PerformancePlotNode`, `YLimDisp`, `SystemCurveNode`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `PerformanceCurve` connect `.density_rel` to `Sprint S4 — Docstrings & doctests (8 h)`, `Sprint S5 — Read the Docs (Sphinx + autodoc) (8 h)`, `PortItem`, `.__init__`, `TestPoint`, `Q_`, `ReportBundle`, `MVP use cases`, `test_compliance_gui.py`, `unit_conversion.py`, `PerformanceFitter`, `YLimDisp`, `QPushButton`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `make_node()` (e.g. with `.__init__()` and `build_scene()`) actually correct?**
  _`make_node()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `BaseNode` (e.g. with `ComplianceCheckNode` and `_Fallback`) actually correct?**
  _`BaseNode` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `PerformanceCurve` (e.g. with `Candidate` and `Catalogue`) actually correct?**
  _`PerformanceCurve` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `quantity_factory()` (e.g. with `test_quantity_factory_canonicalizes_capacity()` and `test_quantity_factory_rejects_non_quantity()`) actually correct?**
  _`quantity_factory()` has 12 INFERRED edges - model-reasoned connections that need verification._