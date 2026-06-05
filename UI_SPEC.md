# UI Specification — API 610 Pump Performance Workbench

> **Target implementer:** a coding agent building a desktop visual‑workflow
> application on top of the existing `pump` Python library.
> **Paradigm:** an [Orange3](https://orangedatamining.com/)‑style **widget canvas** —
> the user drags nodes onto a canvas and wires them together; data flows along the
> links. Each widget wraps one step of the engineering workflow defined in
> `examples/pump_api610_performance 1.ipynb`.

---

## 1. Goal & Scope

Build a graphical, node‑based application that lets a mechanical/rotating‑equipment
engineer reproduce the **API 610 (12th ed.) / ISO 13709** Factory Acceptance Test
(FAT) performance assessment **without writing code**, by assembling a visual
pipeline of widgets.

The application must:

1. Capture the **rated (design) point** and the **measured test points** of a
   centrifugal pump.
2. Correct measured points to rated speed/density/viscosity via the **affinity
   laws**.
3. Fit performance curves (**3rd‑degree least‑squares polynomial** and **natural
   cubic spline**) for Head, Power and Efficiency vs. Capacity.
4. Visualize **Q×H, Q×P, Q×η** curves with the rated point marked.
5. Evaluate **deviations against API 610 tolerances** and render an APPROVED /
   REJECTED verdict.
6. Export a reusable **data file (JSON)** and a formatted **`.docx` report**.

The engineering math **must reuse the existing `pump` library** (see
§4 *Library Binding*). The UI is a thin orchestration + visualization layer; it
must not re‑implement physics that the library already provides.

### Non‑goals
- No new physics or correlations beyond what the library/notebook already contain.
- No multi‑user, cloud, or database features. Single‑user desktop tool.
- No authentication.

---

## 2. Reference Workflow (from the notebook)

The notebook `pump_api610_performance 1.ipynb` is the **canonical workflow** and the
UI must mirror its seven stages:

| # | Notebook stage | UI widget (see §5) |
|---|----------------|--------------------|
| 1 | Configure environment | *(implicit — app startup)* |
| 2 | Input: rated point + test points | **Rated Point Input**, **Test Points Table** |
| 3 | Correct points to rated speed (affinity laws) | **Speed / Affinity Correction** |
| 4 | Curve fit: polynomial deg‑3 + natural cubic spline | **Curve Fit** |
| 5 | Visualizations Q×H, Q×P, Q×η | **Performance Plot** |
| 6 | API 610 deviation & tolerance evaluation | **API 610 Compliance Check** |
| 7 | Export report (data file) | **Report Export** |

A pre‑wired **default pipeline** must be shipped so a new user sees the full chain
already connected on first launch:

```
[Rated Point Input] ─┐
                     ├─► [Speed/Affinity Correction] ─► [Curve Fit] ─┬─► [Performance Plot]
[Test Points Table] ─┘                                               ├─► [API 610 Compliance Check]
                                                                     └─► [Report Export]
```

### Multiple pumps sharing one rated point & fluid (A/B units)

A common API 610 case is testing **two (or more) physical pumps against the same
rated point and the same fluid** — e.g. parallel‑operation A/B units. The graph
must support this **without duplicating the rated point**: a single
**Rated Point Input** fans its `RatedPoint` signal out to **one test branch per
pump**, and all branches **merge into a single Report Export** node (whose
multi‑input port keys each dataset by the pump TAG, exactly as
`ReportGenerator` already expects — see §5.7):

```
                          ┌─► [Test Points Table · Pump A] ─► [Correction A] ─► [Curve Fit A] ─► [Check A] ─┐
[Rated Point Input] ──────┤                                                                                 ├─► [Report Export]
   (shared rated + fluid) └─► [Test Points Table · Pump B] ─► [Correction B] ─► [Curve Fit B] ─► [Check B] ─┘
```

- The shared **rated point and fluid are entered once** and reused by every
  branch; editing them re‑evaluates all pumps reactively.
- Each pump has its **own measured test points** and therefore its own corrected
  curve, fit, plot and verdict.
- The combined report contains one **Test Data — `<TAG>`** section per pump plus a
  consolidated header, and the overall acceptance status reflects **all** pumps.
- Adding a third pump is just dragging another Test Points Table branch and wiring
  it to the same Rated Point Input and the same Report Export.

---

## 3. Data Model & Inter‑widget "Signals"

Following Orange's model, widgets communicate by emitting and consuming typed
**signals** over the links. Define these payload types (plain Python objects /
dataclasses serializable to JSON):

| Signal type | Produced by | Consumed by | Payload |
|-------------|-------------|-------------|---------|
| `RatedPoint` | Rated Point Input | Correction, Fit, Check, Report | TAG, Q, H, N, P, η, head‑shutoff, rated density (rel + abs), nominal viscosity, pressure unit, standard label, parallel‑operation flag |
| `TestPointSet` | Test Points Table | Correction | **pump TAG** (the physical unit, e.g. `B‑2351105A`) + list of raw measured rows (Q, P_suc, P_dis, T_water, N, P, optional η/Head) + pressure unit |
| `CorrectedCurve` | Speed/Affinity Correction | Curve Fit, Plot, Report | pump TAG + a `pump.PerformanceCurve` (points corrected to rated speed) + the `Fluid` used |
| `FittedModel` | Curve Fit | Plot, Check, Report | pump TAG + polynomial coeffs (H, P, η) + spline objects + the `PerformanceCurve` + chosen degree |
| `ComplianceResult` | API 610 Compliance Check | Report | pump TAG + per‑parameter actual/predicted/deviation/tolerance/verdict + per‑pump overall verdict |
| `ReportBundle` | (assembled in Report Export) | — | shared rated point/fluid + **one entry per pump TAG**, ready for `.docx`/JSON serialization |

**Identity convention:** `RatedPoint.TAG` is the **service / datasheet** tag and is
*shared*; each `TestPointSet.TAG` is the **physical unit** tag and is *unique per
branch*. Every downstream signal carries its branch's pump TAG so the Report Export
can key datasets without ambiguity. The pump TAG also labels each plot/verdict so
the user can tell branches apart on the canvas.

**Rules**
- Signals are **immutable**: a widget recomputes and re‑emits a fresh payload when
  its inputs or settings change (matching the library's "always return a new
  instance" convention in `PerformanceCurve.to_speed` / `to_fluid`).
- Re‑emission propagates **downstream automatically** (reactive graph). Changing a
  field in Rated Point Input must live‑update the plot and the verdict — and when
  the rated point fans out to several pumps, **every** branch re‑evaluates.
- **Fan‑out:** one output port may connect to many downstream nodes (the shared
  `RatedPoint` drives N test branches). **Merge:** the Report Export input port is
  **multi‑connection** — it accepts a `ComplianceResult`/`FittedModel` from each
  branch and collects them into a list keyed by pump TAG. Connecting/disconnecting
  a branch adds/removes that pump from the report with no other rewiring.
- Each widget shows a **status line** (Orange‑style) summarizing its output
  (e.g. "Pump A · 5 points · corrected to 1750 rpm" or "❌ 1 parameter out of tolerance").

---

## 4. Library Binding (mandatory)

The UI must call into `pump` rather than duplicate logic. Key bindings:

| UI concept | Library entry point |
|------------|---------------------|
| Fluid (test water / rated fluid) | `pump.Fluid(name, density=Q_(...), viscosity=Q_(...))` |
| Rated / design point | `pump.DesignPoint(fluid, capacity=Q_, differential_head=Q_, head_shutoff=Q_, breaking_power=Q_, ...)` |
| Measured / corrected point | `pump.TestPoint(fluid, capacity=Q_, speed_of_rotation=Q_, _head=Q_, breaking_power=Q_, ...)` |
| Head from suction/discharge pressures | `TestPoint.pressure_head` / `compute_head` (TDH = pressure + velocity + elevation head) |
| Hydraulic power & efficiency | `TestPoint.hydraulic_power`, `TestPoint.efficiency` |
| Collection of points | `pump.PerformanceCurve(fluid, points, polynomial_degree=3)` |
| Affinity‑law speed correction | `PerformanceCurve.to_speed(Q_(N_rated, "rpm"))` |
| Density/fluid correction | `PerformanceCurve.to_fluid(rated_fluid)` |
| Polynomial fit + predictions | `PerformanceCurve.fitter.*_coeffs`, `predict_head/efficiency/breaking_power`, `predicted_data` |
| Built‑in matplotlib curve | `PerformanceCurve.plot_performance_curve(capacity=, return_io=True, *_ylim=)` |
| Tolerance limits & verdict tables | `pump.PerformanceChecker(design_point, curve)` → `acceptable_limits`, `check_summary`, `test_summary_with_limits`, `report_summary` |
| `.docx` report (EN/PT) | `pump.ReportGenerator(language=, template_path=).generate_report(report_data, output_file=)` |
| Units everywhere | `pump.Q_` + `quantity_factory`; honor `STANDARD_UNITS` (capacity m³/h, head m, power kW, efficiency %, speed rpm, pressure kgf/cm² or bar) |

> **Note on tolerances:** the library's `PerformanceChecker` encodes head ±3 %,
> shutoff tolerance by head band (≤75 m → 10 %, ≤300 m → 8 %, else 5 %), power
> +4 %. The notebook uses power band (≤75→3 %, ≤300→8 %, else 5 %). The
> **library's `PerformanceChecker` is the source of truth**; expose its
> tolerances as editable defaults in the Compliance Check widget (§5.6) and warn
> if the user overrides them.

> **Spline:** the library only ships polynomial fitting. The natural cubic spline
> from the notebook (cell 8, `NaturalCubicSpline`) is **not** in `pump` — port it
> into the UI layer (or, preferred, contribute it to `pump`) as a secondary fit
> the user can toggle. Polynomial degree‑3 is the API‑610 default and must be the
> primary curve.

---

## 5. Widget Catalog

Each widget below specifies: **Inputs → Outputs**, the **control panel** (left
settings pane), the **main area** (canvas/preview), and **validation**. All
widgets follow the Orange convention: a compact icon node on the canvas, and a
double‑click‑to‑open property dialog.

### 5.1 Rated Point Input
- **Inputs:** none (source node). Optional: a loaded JSON file.
- **Outputs:** `RatedPoint`.
- **Controls:**
  - TAG (text), Standard label (text, default `"API610 (12a ed.) / ISO 13709 + N-553"`).
  - Q [m³/h], H [m], N [rpm], P [kW], η [%] (optional), Head shutoff [m] (optional).
  - Rated density — entered as relative density **and** kg/m³ (auto‑convert, keep
    in sync), nominal viscosity [cSt].
  - Pressure unit selector: `kgf/cm²` | `bar` (drives `pressure_to_head`).
  - Parallel‑operation checkbox.
- **Validation:** Q ≥ 0, H > 0, N > 0, P > 0; show inline errors; node turns amber
  on invalid and emits nothing.
- **Binding:** constructs a `Fluid` (rated) + `DesignPoint`.

### 5.2 Test Points Table
- **Inputs:** none (source). Optional JSON file.
- **Outputs:** `TestPointSet`.
- **Controls:** a **Pump TAG** field identifying the *physical unit* under test
  (e.g. `B‑2351105A`). This is what distinguishes one branch from another when
  several pumps share the rated point; it must be unique among connected branches
  (warn on collision) and defaults to the rated TAG with an `A`, `B`, … suffix.
- **Main area:** an **editable spreadsheet‑like grid**, one row per measured point:
  `Q [m³/h] · P_suction · P_discharge · T_water [°C] · N [rpm] · P [kW] · (Head, η — computed/optional)`.
  - Add/remove/reorder rows; paste from clipboard (Excel‑friendly);
  - Accept comma **or** dot decimal separators (the example JSON uses
    `"858,29"` style) and trim/parse to float.
  - A read‑only computed column shows **Head = (P_dis − P_suc)/(ρ·g)** using the
    water density at `T_water` (port the notebook's `water_density_kgm3`
    polynomial) and the selected pressure unit — live as the user types.
- **Validation:** at least 3 points required for a degree‑3 fit (block fit with a
  clear message otherwise); warn if a shutoff point (Q≈0) is missing.

### 5.3 Speed / Affinity Correction
- **Inputs:** `RatedPoint`, `TestPointSet`.
- **Outputs:** `CorrectedCurve`.
- **Controls:** target speed (default = rated N, editable), toggles for which
  corrections to apply: speed (affinity), density (ρ_rated/ρ_test), viscosity
  (nominal‑viscosity factors). Show the affinity formulas as read‑only reference:
  Q∝N, H∝N², P∝N³.
- **Main area:** before/after table (measured vs corrected Q,H,P,η) — mirror the
  notebook's printed correction table.
- **Binding:** build `TestPoint`s from the raw rows, wrap in
  `PerformanceCurve(test_fluid, points, polynomial_degree=3)`, then
  `.to_speed(Q_(N_target,"rpm"))` and `.to_fluid(rated_fluid)`.

### 5.4 Curve Fit
- **Inputs:** `CorrectedCurve`.
- **Outputs:** `FittedModel`.
- **Controls:** polynomial degree (default **3**, range 2–5), spline on/off,
  resolution of the smooth curve.
- **Main area:** show fitted coefficients for H, P, η and R²/residual summary;
  small inline preview of the three fits.
- **Binding:** `PerformanceCurve.fitter.head_coeffs / power_coeffs /
  efficiency_coeffs`; spline ported from notebook (`NaturalCubicSpline`).

### 5.5 Performance Plot
- **Inputs:** `FittedModel` (and `RatedPoint` for the marker).
- **Outputs:** optional `image/png` (BytesIO) for the report.
- **Main area:** three stacked, shared‑x charts **Q×H (tallest), Q×P, Q×η**, each
  with: corrected data points (markers), polynomial curve, spline curve (dashed),
  and a crosshair at the rated capacity with value labels.
- **Controls:** per‑axis y‑limits, title, toggle polynomial/spline/points,
  "Copy/Export PNG".
- **Binding:** prefer `PerformanceCurve.plot_performance_curve(capacity=rated_Q,
  return_io=True, head_ylim=, power_ylim=, efficiency_ylim=)` for the report image;
  the on‑canvas interactive version may overlay the spline that the library plot
  lacks.

### 5.6 API 610 Compliance Check
- **Inputs:** `FittedModel`, `RatedPoint`.
- **Outputs:** `ComplianceResult`.
- **Main area:** a results table, one row per evaluated parameter
  (**Head**, **Power**, **Efficiency**, **Shutoff Head**), columns:
  *Actual (rated) · Predicted (from curve) · Min · Max · Deviation · Tolerance ·
  Verdict (✅/❌)*; plus a bold **overall verdict** banner.
  - Deviation per notebook: `δ = 1 − nominal/predicted`.
  - Verdict logic per notebook `status()`: head |δ|≤tol; power δ≤tol;
    efficiency δ≥−tol.
- **Controls:** editable tolerance fields pre‑filled from
  `PerformanceChecker` defaults (head 3 %, shutoff by band, power 4 %); a
  reset‑to‑standard button; warning chip if user overrides defaults.
- **Binding:** `PerformanceChecker(design_point, curve)` →
  `acceptable_limits`, `test_summary_with_limits`, `check_summary`,
  `report_summary`.

### 5.7 Report Export
- **Inputs:** the shared `RatedPoint`, plus a **multi‑connection** input that
  accepts one branch bundle (`CorrectedCurve` + `FittedModel` + `ComplianceResult`
  + plot PNG) **per pump**. One connected branch → single‑pump report; N branches →
  one consolidated report covering all units.
- **Outputs:** files on disk.
- **Controls:**
  - **Equipment description** key/value editor — **per pump TAG** (a sub‑table for
    each connected branch: manufacturer, model, serial, etc.), since two physical
    units differ even when the service is the same.
  - Language: **EN | PT** (drives `ReportGenerator(language=...)` and the
    `template_en.docx`/`template_pt.docx`).
  - Output folder + filename. Default `Report_<service-TAG>_<dd-mm-YYYY>.docx` for a
    multi‑pump report, or `Report_<pump-TAG>_…` when a single branch is connected.
  - Buttons: **Export `.docx`**, **Export `.json`** (reusable data file matching
    the schema in §6), **Export PNG**.
- **Binding:** assemble the `report_data` dict shaped exactly as
  `ReportGenerator.generate_report` expects — the design point is shared, and
  `test_data` gets **one keyed entry per pump TAG** (the loop
  `for tag, test_data in report_data["test_data"].items()` in `generate_report`
  already renders a *Test Data — `<TAG>`* section for each):
  ```python
  {
    "equipment_description": {"TAG": "<service-TAG>", ...},
    "design_point": <DesignPoint>,            # shared rated point + fluid
    "test_data": {
        "<pump-A-TAG>": {
            "test_summary": <report_summary dict>,       # from Check A
            "test_data":    <PerformanceCurve.test_data>, # from Correction/Fit A
            "Performance Curve": <BytesIO PNG>,           # from Plot A
        },
        "<pump-B-TAG>": {
            "test_summary": <report_summary dict>,        # from Check B
            "test_data":    <PerformanceCurve.test_data>, # from Correction/Fit B
            "Performance Curve": <BytesIO PNG>,           # from Plot B
        },
    }
  }
  ```

---

## 6. Persistence

### 6.1 Project file (the canvas)
Save/Load the **whole workflow** (node positions, links, every widget's settings
and entered data) to a single `.pumpflow` JSON file. Re‑opening restores the
pipeline and recomputes downstream signals.

### 6.2 Data‑exchange JSON
The **Test Points Table** and **Rated Point Input** widgets must round‑trip a
simple JSON data file with the following shape (note the locale‑style
comma‑decimal string values, which the importer must parse):

```json
{
  "unit": "bar",
  "rated": { "tag": "...", "q_m3h": "833", "head_m": "73", "n_rpm": "1750",
             "power_kw": "252", "dens_rel": "0,736", "visc_nom_cst": "0,567",
             "head_shutoff": "117" },
  "points": [
    { "q": "858,29", "p_suc": "1,81", "p_dis": "9,47", "temp_c": "34",
      "head": "78.552", "power": "298,69", "n_rpm": "1799" }
  ]
}
```
- Importer must accept the comma‑decimal strings shown above.
- Exporter should emit the same shape so existing `.json` files and the new tool
  stay interoperable. The richer §7 report bundle (corrected points, predictions,
  deviations, verdict) extends — but does not break — this format.

---

## 7. Cross‑cutting Requirements

- **Reactive recompute:** editing any upstream value re‑runs the downstream graph
  and refreshes plots/verdict within ~200 ms for the typical ≤10‑point dataset.
- **Units:** all displayed quantities carry units and follow `STANDARD_UNITS`
  (capacity m³/h, head m, power kW, η %, speed rpm). Pressure input toggles
  kgf/cm² ↔ bar. Never show a bare number where a unit is expected.
- **Localization:** UI labels and the report both support **EN and PT‑BR** (the
  library already ships `locales/en` and `locales/pt` + `template_en/pt.docx`).
- **Validation & safety:** widgets emit nothing while inputs are invalid; nodes
  surface an amber/red state with a tooltip explaining what's missing
  (mirrors the notebook's `[AVISO] Execute o formulário…` guards).
- **Error surfaces:** library exceptions (e.g. `ValueError: All TestPoints must
  have the same fluid`, missing `breaking_power`) are caught and shown as
  human‑readable widget errors, not stack traces.
- **Determinism:** given the same inputs, the verdict and exported files are
  byte‑reproducible (fixed number formatting, `:0.02f~P` style as the library uses).

---

## 8. Suggested Tech Stack

- **Library/runtime:** Python 3.12 (matches `environment.yml`), the existing
  `pump` package as a dependency, `pint`, `numpy`, `matplotlib`, `python-docx`,
  `tabulate`.
- **Canvas framework:** a **standalone, lightweight node‑graph desktop app** built
  on **PySide6 (Qt)** plus a node‑editor library such as
  [NodeGraphQt](https://github.com/jchanvfx/NodeGraphQt). This keeps the Orange3
  *paradigm* (drag‑and‑wire widgets, reactive signal flow) without pulling in the
  full Orange3 runtime — the goal is a small, self‑contained binary, not an Orange
  add‑on. Do **not** depend on `Orange3`/`orangewidget`.
- **Packaging:** ship as a single self‑contained executable
  (PyInstaller/Briefcase) so the engineer can run it without a Python install.
  Keep the dependency tree minimal (Qt + matplotlib + the `pump` library and its
  existing deps; no heavy data‑science stack).
- Charts via matplotlib embedded in the canvas (Qt `FigureCanvas`), reusing
  `plot_performance_curve` for the report image.

---

## 9. Acceptance Criteria

A reviewer must be able to, **end‑to‑end and only via the GUI**:

1. Enter (or import from a JSON data file, §6.2) a rated point plus its measured
   test points into the Rated + Test widgets.
2. See the corrected points after affinity correction to the rated speed.
3. See degree‑3 polynomial **and** spline curves on Q×H, Q×P, Q×η with the rated
   point marked.
4. Read an API 610 verdict table whose numbers match
   `PerformanceChecker(...).report_summary` / `test_summary_with_limits` for the
   same inputs.
5. Export a `.docx` report identical in structure to the repo's existing
   `Report_*.docx`, and a `.json` that re‑imports cleanly.
6. Save the canvas, reopen it, and recover the identical pipeline and results.
7. **Two‑pump case:** add a second Test Points Table (Pump B) with its own measured
   data, wire it to the **same** Rated Point Input and the **same** Report Export,
   and obtain a single `.docx` containing a separate *Test Data — `<TAG>`* section,
   plot and verdict for **each** pump — all sharing the one rated point and fluid,
   with the rated point entered only once.
