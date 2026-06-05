# Module Reference

Full API documentation for the `pumpflow` package, organized by module. Types
shown are the public surface; private helpers (leading underscore) are noted only
where useful.

---

## `pumpflow` (package)

Package metadata. Exposes `__version__` (`"0.1.0"`). The module docstring is the
authoritative map of the package layout.

## `pumpflow.__main__`

Enables `python -m pumpflow`; calls `pumpflow.app.run()`.

---

## `pumpflow.signals` — typed payloads (UI_SPEC §3)

Immutable `@dataclass(frozen=True)` payloads that travel along canvas links. A
node re-emits a fresh instance whenever inputs or settings change.

### `RatedPoint`
The shared rated/design point + rated fluid.

| Field | Type | Notes |
|---|---|---|
| `tag` | `str` | **service / datasheet** TAG (shared across branches) |
| `standard` | `str` | e.g. `"API610 (12a ed.) / ISO 13709 + N-553"` |
| `q_m3h`, `head_m`, `speed_rpm`, `power_kw` | `float` | rated duty |
| `efficiency_pct`, `head_shutoff_m` | `float \| None` | optional |
| `density_rel`, `viscosity_cst` | `float` | rated fluid |
| `pressure_unit` | `str` | `"bar"` or `"kgf/cm**2"` |
| `parallel_operation` | `bool` | A/B flag |

- `density_kgm3` *(property)* → `density_rel * 1000`.
- `is_valid()` → `(bool, str)`; enforces Q ≥ 0, H > 0, N > 0, P > 0, density > 0,
  non-empty TAG (UI_SPEC §5.1).

### `TestRow` / `TestPointSet`
`TestRow` is one raw measured row (`q_m3h`, `p_suction`, `p_discharge`, `temp_c`,
`speed_rpm`, `power_kw`, optional `head_m`/`efficiency_pct`).
`TestPointSet` groups rows for **one physical pump**:

- `pump_tag` — unique per branch.
- `rows: tuple[TestRow, ...]`, `pressure_unit`.
- `is_valid()` → requires ≥ 3 rows (degree-3 fit) and a TAG.
- `has_shutoff()` → True if a Q ≈ 0 row exists.

### `CorrectedCurve`
`pump_tag`, `curve` (a `pump.PerformanceCurve`), `fluid`, `target_speed_rpm`, and
`before_after` (tuple of `{measured, corrected}` dicts for the correction table).

### `FittedModel`
`pump_tag`, `curve`, `degree`, `head_coeffs`/`power_coeffs`/`efficiency_coeffs`
(`np.ndarray`), optional `*_spline` (`NaturalCubicSpline`), and `r2` dict.

### `ParameterCheck` / `ComplianceResult`
`ParameterCheck` is one verdict row: `name`, `actual`, `predicted`, `minimum`,
`maximum`, `deviation`, `tolerance`, `passed`.
`ComplianceResult`: `pump_tag`, `parameters`, `overall_pass`, `tolerances`,
`overridden`; `verdict_label` *(property)* → `"APPROVED"`/`"REJECTED"`.

### `BranchBundle` / `ReportBundle`
`BranchBundle` collects one branch's `corrected`/`fitted`/`compliance`/`plot_png`/
`equipment`. `ReportBundle` holds the shared `rated` + a tuple of branches;
`overall_pass` is True only when **every** branch passes.

`with_changes(obj, **changes)` — thin wrapper over `dataclasses.replace`.

---

## `pumpflow.binding` — the bridge into `pump` (UI_SPEC §4)

The single module that imports the `pump` library. Raises `BindingError`
(human-readable) on validation/library failures.

| Function | Purpose |
|---|---|
| `make_rated_fluid(rated)` | build the rated `pump.Fluid` |
| `make_design_point(rated, fluid=None)` | build the shared `pump.DesignPoint` |
| `pressure_to_pa(value, unit)` | pressure-unit → Pascal |
| `row_head_m(row, unit)` | `Head = (P_dis−P_suc)/(ρ·g)` (water ρ at row T) |
| `row_efficiency_pct(row, head)` | hydraulic/breaking η |
| `correct_curve(rated, tps, …)` | `TestPoint`s → `PerformanceCurve` → `to_speed` → `to_fluid` |
| `fit_model(corrected, degree, with_spline)` | coeffs + splines + R² |
| `default_tolerances(rated)` | API 610 head-band shut-off tolerance + defaults |
| `check_compliance(fitted, rated, tolerances=None)` | deviations + verdict via `PerformanceChecker` |
| `build_report_png(corrected, rated, ylims=None)` | library Matplotlib plot → BytesIO PNG |
| `report_summary_for(fitted, rated)` | `PerformanceChecker.report_summary` |
| `assemble_report_data(rated, bundles, equipment=None)` | the `report_data` dict for `ReportGenerator` |
| `generate_docx(report_data, language, template_path, output_file)` | call `ReportGenerator` |

**Deviation** convention: `δ = 1 − nominal/predicted`. Pass rules — Head `|δ|≤tol`,
Power `δ≤tol`, Efficiency `δ≥−tol`, Shut-off `|δ|≤tol`.

---

## `pumpflow.mathx` — ported maths (UI_SPEC §4 note)

- `water_density_kgm3(temp_c)` — 4th-order water-density polynomial (placeholder
  coefficients; swap in exact ones if available).
- `NaturalCubicSpline(x, y)` — natural cubic spline (2nd derivative 0 at ends);
  callable, with `.sample(n)`. Sorts and collapses duplicate abscissae.
- `r_squared(y_actual, y_pred)` — coefficient of determination.

## `pumpflow.numfmt`

- `parse_decimal(value, default=None)` — accepts `,`/`.` decimals + thousands
  separators (Excel-paste friendly).
- `fmt(value, decimals=2, unit="")`, `fmt_pct(value, decimals=1)` — display
  formatting; `None` → `"—"`.

## `pumpflow.sample_data`

`SINGLE_PUMP_JSON` (UI_SPEC §6.2 shape, with deliberate comma-decimals) and
`SECOND_PUMP_POINTS` (the Pump B unit for the A/B demo).

## `pumpflow.persistence` — file IO (UI_SPEC §6)

- `rated_from_json(doc)` / `testset_from_json(doc, pump_tag=None)` — §6.2 → signals.
- `json_from_signals(rated, tps=None)` — signals → §6.2 dict.
- `read_json(path)` / `write_json(path, doc)` — generic JSON IO (the scene uses
  these for `.pumpflow`).

---

## `pumpflow.canvas`

### `theme`
Palette (`QColor`s), per-signal `PORT_COLORS`, metrics (`NODE_W`, `TITLE_H`,
`ROW_H`, `PORT_R`, `GRID_SIZE`), and font helpers.

### `PortItem` *(QGraphicsObject)*
A typed connection point. Key: `is_output`, `multi`, `edges`, `signal_type`;
`can_accept(other)` enforces the compatibility rules; `center_scene()` for link
geometry; `add_edge`/`remove_edge`.

### `EdgeItem` *(QGraphicsPathItem)*
A bezier link. `attach()`/`detach()` register with both ports; `set_drag_end(pos)`
animates an in-progress drag; `update_path()` recomputes the curve; `other(port)`.

### `NodeItem` *(QGraphicsObject)*
Renders one widget: title bar (steel; lighter for source nodes), icon glyph, port
labels, and a **status line** with a colored state dot. `mouseDoubleClickEvent`
asks the scene to open the property dialog. Builds/positions `PortItem`s from the
logic's `inputs`/`outputs`.

### `GraphView` *(QGraphicsView)*
Pan (middle / Alt+drag), zoom (wheel), dotted grid, and **all interactive edge
creation** (press-drag-release on ports, with single-input re-wire). Tolerant
14 px port hit-testing.

### `GraphScene` *(QGraphicsScene)*
The orchestration core.

| Member | Role |
|---|---|
| `add_node(kind, pos, node_id=None, settings=None)` | instantiate via factory |
| `remove_node`, `node_by_id` | node management |
| `connect_ports(src, dst)` | orientation-tolerant link creation |
| `remove_edge` | link removal |
| `evaluate()` | topological recompute of all nodes |
| `to_dict()` / `load_dict(doc)` | `.pumpflow` (de)serialization |
| signals: `graph_changed`, `dialog_requested(logic)` | UI wiring |

Pressing **Delete/Backspace** removes selected nodes/links then re-evaluates.

---

## `pumpflow.nodes`

### `base.BaseNode` + `PortSpec`
`PortSpec(name, signal_type, multi=False)` declares a port. `BaseNode` carries
class metadata (`kind`, `title`, `glyph`, `is_source`, `inputs`, `outputs`) and:

- `default_settings()` → dict (override).
- `compute(inputs) -> {port: payload}` (override) — the node's logic.
- `port_label(name)`, `create_dialog(parent, on_change)` (override).
- `run(inputs)` — wraps `compute`, fills `outputs_cache`.
- `set_error(msg)`, `emit_nothing(status, state)` — state helpers (UI_SPEC §7).
- `first(inputs, name)`, `all_of(inputs, name)` — input gatherers.
- `serialize_settings()`, `load_settings(data)` — persistence hooks.

State values: `idle` · `ok` · `invalid` · `error` · `reject`.

### `ui` — dialog building blocks
`PropertyDialog` (scrollable, header + body), `Banner` (info/ok/warn/error),
`section`, `hline`, `row`, `line_edit`, `spin`, `int_spin`, `combo`, `checkbox`.

### `plotting.build_figure(fitted, rated=None, …)`
Shared Matplotlib figure builder: stacked, shared-x Q×H / Q×P / Q×η charts with
data points, polynomial, dashed spline, and a rated-capacity crosshair. `compact`
mode for in-dialog previews.

### `registry`
`NODE_KINDS` (the toolbox catalog) and `make_node(kind)` factory.

### The seven widget nodes

| Module · class | `kind` | Inputs → Outputs |
|---|---|---|
| `rated_point.RatedPointInputNode` | `rated_point` | — → `RatedPoint` |
| `test_points.TestPointsTableNode` | `test_points` | — → `TestPointSet` |
| `correction.SpeedCorrectionNode` | `correction` | `RatedPoint`, `TestPointSet` → `CorrectedCurve` |
| `curve_fit.CurveFitNode` | `curve_fit` | `CorrectedCurve` → `FittedModel` |
| `performance_plot.PerformancePlotNode` | `performance_plot` | `FittedModel`, `RatedPoint` → `image` |
| `compliance.ComplianceCheckNode` | `compliance` | `FittedModel`, `RatedPoint` → `ComplianceResult` |
| `report_export.ReportExportNode` | `report_export` | `RatedPoint`, `branch`* (multi) → — |

Each node's `compute()` validates inputs, calls `binding` where physics is
needed, sets a one-line `status` + `state`, and returns its typed payload. Each
`create_dialog()` returns a `PropertyDialog` wired to live-apply via `on_change`.

---

## `pumpflow.style`
`APP_QSS` — the global Qt stylesheet (light industrial-steel theme): toolbar,
toolbox, dialogs, inputs, tables, banners, the verdict banner, and scrollbars.

## `pumpflow.app`

### `MainWindow`
Hosts the scene/view, menu bar (File / Add node / Canvas), the **Widgets** toolbox
dock, and the status bar.

| Method | Role |
|---|---|
| `build_default_pipeline()` | clear + lay out and wire the 7-node default graph |
| `add_second_pump_branch()` | the A/B demo branch (Pump B) |
| `add_node_centered(kind)` | drop a node at the viewport center |
| `save_project` / `open_project` | `.pumpflow` IO |
| `import_data_file` / `export_data_file` | §6.2 JSON IO |
| `_open_dialog(logic)` | build + exec a node's property dialog, then re-evaluate |

### `run() -> int`
Creates the `QApplication`, applies `APP_QSS`, shows `MainWindow`, runs the event
loop. Returned by `python -m pumpflow`.
