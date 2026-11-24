# Code Review — Toward the Next-Generation Tool

- **Date:** 2026-07-13
- **Scope:** `pump/` library (point, performance_curve, unit_conversion, fluid, report) and the `pump ↔ pumpflow` boundary (`pumpflow/binding.py`).
- **Baseline:** branch `orange`, test suite green at review time (46 passed, 2 GUI-only skips). No CI configured.
- **Nature:** review only — findings and options, **no code was changed**. Each finding has a suggested action for the maintainer to implement.
- **Relationship to ADRs:** the ADR backlog ([docs/adr/](../adr/README.md), 0001–0010) already registers the big structural decisions (test harness, pint registry, god-class split, point hierarchy, `hasattr` schema, ACL leak, node SRP, mathx promotion, versioning). This review does **not** re-litigate those; it adds concrete new findings (F-01…F-18) and frames the strategic options (§3). Where a finding strengthens an existing ADR, it says so.

---

## 1. Findings index

| ID | Severity | Area | One-liner |
|---|---|---|---|
| F-01 | 🔴 High | Checker | `acceptable_limits` crashes when shutoff/power data is absent |
| F-02 | 🔴 High | Checker | `check_summary` applies the rated ±3% head band to *every* point |
| F-03 | 🔴 High | Curve | `test_data` gates columns on point[0] but iterates all points |
| F-04 | 🔴 High | Curve | `to_fluid` hard-requires `speed_of_rotation` and silently drops power |
| F-05 | 🟠 Medium | Compliance | Two inconsistent acceptance criteria: deviation-vs-predicted (UI) vs limits-vs-rated (library) |
| F-06 | 🟠 Medium | Fitting | No degree-vs-point-count validation; library default (4) ≠ UI default (3) |
| F-07 | 🟠 Medium | Fitting | Shutoff head is a silent polynomial extrapolation at Q = 0 |
| F-08 | 🟠 Medium | Curve | Fitter receives the *unsorted* points list; `curve.points` ≠ `curve.fitter.points` |
| F-09 | 🟠 Medium | Points | Verb-named *properties* mutate state (`compute_head`, `pressure_head` writes `delta_pressure`) |
| F-10 | 🟠 Medium | Binding | Physics & tolerance logic duplicated in `binding.py` despite the "no re-implementation" rule |
| F-11 | 🟡 Low | Units | Two Pint registries coexist (`ureg` vs application-registry `Q_`) |
| F-12 | 🟡 Low | Units | `convert()` re-parses every standard unit on every call |
| F-13 | 🟡 Low | Units | Attribute-name context routing can silently change units on a typo |
| F-14 | 🟡 Low | Constants | Three gravity constants (`9.81` ×2 in points, `9.81` in binding) |
| F-15 | 🟡 Low | Report | `setlocale` global side effect, `print()` in library, same-day filename overwrite |
| F-16 | 🟡 Low | Strings | User-facing typos: "Head Shuttoff", "Hydralic Power", module docstring "peroformance_curve" |
| F-17 | 🟡 Low | Hygiene | Dead commented-out block in `to_speed`; `summary()` prints *and* returns |
| F-18 | 🟡 Low | Delivery | No CI; wheel ships `pumpflow` but a plain install cannot import it |

---

## 2. Findings in detail

### 🔴 F-01 — `acceptable_limits` raises instead of degrading
**Where:** `pump/performance_curve.py:701-710`
**What:** `minimum_head_shutoff` / `maximum_head_shutoff` / `maximum_breaking_power` are only assigned by `_compute_limits` when the design point has `head_shutoff` / `breaking_power` (`:685-698`). The dict comprehension guard `if v is not None` never fires: attribute access raises `AttributeError` before the filter can run.
**Why it matters:** any consumer calling `acceptable_limits` on a minimal design point (capacity + head only — a legitimate FAT input) crashes.
**Action:** initialize the optional limits to `None` in `_compute_limits` (or build the dict with `getattr(self, name, None)`), keep the existing `is not None` filter, and add a regression test with a design point that has no shutoff/power data. Same hazard exists inside `check_summary` (`:726` reads `self.minimum_head_shutoff` unguarded when a point has capacity < 0.1 m³/h).

### 🔴 F-02 — Head verdict applied at the wrong altitude
**Where:** `pump/performance_curve.py:722-747` (`check_summary`)
**What:** every test point's head is checked against `minimum_head ≤ head ≤ maximum_head`, i.e. the rated-head ±3% band. A perfectly healthy curve fails the "Head OK" column at shutoff and at run-out, because those points are *supposed* to be far from rated head.
**Why it matters:** API 610 head tolerance applies to the **fitted value at rated capacity**, not to each raw point. The table as printed will show spurious `False` verdicts to a FAT witness — a credibility problem in an acceptance document.
**Action:** evaluate the verdict once, at rated capacity, from `predict_head` (exactly what `report_summary` already does), and either drop the per-point boolean column or relabel it as "within rated band" informational data. Add a test asserting a compliant curve produces no `False` head verdicts.

### 🔴 F-03 — `test_data` builds ragged/crashing columns
**Where:** `pump/performance_curve.py:567-576`
**What:** each optional column is guarded by `hasattr(self.points[0], …)` but the comprehension iterates **all** points. If a later point lacks `breaking_power`, the property raises `AttributeError` mid-comprehension; if only the *first* point lacks it, a valid column is silently dropped. Ragged dicts then flow into `ReportGenerator._add_test_data`, which sizes the table from the `Capacity` column.
**Why it matters:** report generation becomes input-order dependent and can crash or truncate silently.
**Action:** decide the invariant and enforce it in `PerformanceCurve.__init__` (either "all points carry the same optional attributes" — validate and fail fast — or make columns per-point-optional with an explicit placeholder). Ties into ADR-0006 (explicit schema).

### 🔴 F-04 — `to_fluid` is stricter and quieter than `to_speed`
**Where:** `pump/performance_curve.py:531-550`
**What:** two asymmetries with its sibling `to_speed`:
1. `p.speed_of_rotation` is read unconditionally (`:545`) — a point without speed crashes with a bare `AttributeError`, whereas `to_speed` raises a curated message.
2. When a point has `breaking_power` but no cached `_efficiency`, the branch at `:537-539` is skipped and the new point **silently loses** `breaking_power`; a later `predict_breaking_power` on the converted curve then fails far from the cause.
**Why it matters:** the density-correction step is the heart of UC-02; silent data loss here surfaces as a confusing failure three nodes downstream in the workbench.
**Action:** mirror `to_speed`'s explicit-error pattern for missing speed; when power cannot be recomputed for the new fluid, raise (or at minimum warn) rather than dropping the attribute. Cover both with tests.

### 🟠 F-05 — Two acceptance criteria that can disagree at the edge
**Where:** `pumpflow/binding.py:485-489` (`_deviation`), vs `pump/performance_curve.py:689-698` (limits)
**What:** the UI verdict uses `δ = 1 − nominal/predicted` (normalized by the **predicted** value); the library's min/max limits are `rated ± tol·rated` (normalized by the **rated** value). Near the tolerance boundary (e.g. head 3% high) the two disagree by ~`tol²` — a curve can pass one gate and fail the other.
**Why it matters:** the compliance node and the `.docx` limits table must never contradict each other in front of a vendor.
**Action:** standardize on deviation-from-rated (that is what a guarantee tolerance means in API 610), express both the `ParameterCheck.passed` logic and the limit computation from that single definition, and add a boundary test at exactly ±tol.

### 🟠 F-06 — Fit degree is unvalidated and inconsistent
**Where:** `pump/performance_curve.py:39` (default 4) vs `pumpflow/binding.py:189` (default 3)
**What:** nothing checks `polynomial_degree < len(points)`; `np.polyfit` with 5 points and degree 4 interpolates exactly (zero-residual "fit"), and with fewer points it is ill-conditioned. Library and UI also ship different defaults, so "the same data" fits differently depending on the entry path.
**Why it matters:** API 610 8.3.3.4.3 requires "not less than third order" least-squares — an *exact interpolation* through noisy gauge readings is not a least-squares smoothing and can produce wild shutoff extrapolations (see F-07).
**Action:** validate degree against point count in `PerformanceFitter.__init__` with a clear error; pick one default (3, matching the standard's floor and the notebook) defined in a single constant both layers import.

### 🟠 F-07 — Shutoff head is an unlabeled extrapolation
**Where:** `pump/performance_curve.py:274` (`predicted_data`), `pumpflow/binding.py:460`
**What:** shutoff head is obtained by evaluating the head polynomial at `Q = 0`. When the test ran a true shutoff point this is fine; when the lowest measured flow is, say, 40% of rated, this is polynomial extrapolation outside the data hull — precisely where degree-3/4 polynomials misbehave.
**Action:** prefer the measured point when `min(capacity) ≈ 0`; otherwise mark the value as *extrapolated* in `predicted_data` / `ParameterCheck` (a boolean flag is enough) so the report and the compliance node can disclose it. Add a test with data starting at 40% flow.

### 🟠 F-08 — Curve and fitter see different point lists
**Where:** `pump/performance_curve.py:212-213`
**What:** `self.points = sorted(points)` creates a new sorted list, but `PerformanceFitter(points, …)` receives the **original, unsorted** argument. `curve.points` and `curve.fitter.points` are different objects, in different orders.
**Why it matters:** harmless for `polyfit` (order-invariant) but a landmine for anything order-sensitive added later (splines — a roadmap item via ADR-0009 — plotting, per-index pairing like `binding.correct_curve`'s zip of measured/corrected rows).
**Action:** construct the fitter from `self.points`. One-line fix, plus an identity assertion in tests.

### 🟠 F-09 — Reads that write
**Where:** `pump/point.py:315-345` (`pressure_head` assigns `self.delta_pressure`), `:413-428`, `:456-469`, `:490-512` (`compute_*` are properties that mutate `_head` / `_hydraulic_power` / `_efficiency`)
**What:** verb-named *properties* with side effects. `hasattr(point, "delta_pressure")` returns a different answer after merely reading `pressure_head`; `compute_head` looks like a method but is accessed as an attribute.
**Why it matters:** caching-by-attribute is the mechanism the whole `_head`-pinning convention rides on (CLAUDE.md documents it), so it must at least be *predictable*. Property reads that mutate make debugging and pickling/serialization surprising, and confuse the `hasattr`-driven logic elsewhere (F-03).
**Action:** convert `compute_*` to explicit methods (keep thin `head`/`efficiency` properties over the cache), or adopt `functools.cached_property` and delete the manual cache plumbing. Do the same for `pressure_head`'s hidden write. This is the concrete implementation slice of ADR-0005/0006.

### 🟠 F-10 — The binding re-implements what the library owns
**Where:** `pumpflow/binding.py:59-67` (`G`, `_PA_PER`), `:136-175` (`row_head_m`, `row_efficiency_pct`), `:369-378` (`default_tolerances` re-derives the shutoff band already in `PerformanceChecker._get_shutoff_tolerance`)
**What:** head-from-pressures, efficiency, pressure-unit conversion, and the API 610 shutoff-tolerance bands each exist twice — once in `pump`, once re-typed in the binding with raw floats.
**Why it matters:** violates the repo's own prime constraint ("`pumpflow` must not re-implement physics"). The duplicated tolerance table is the riskiest: change the band edges in one place and the UI's editable defaults diverge from the checker's verdict.
**Action:** promote per-row head/efficiency helpers and a `tolerances_for(design_point)` accessor into `pump` (natural companions to ADR-0007/0009), then shrink `binding.py` to pure payload adaptation. Pressure conversion should go through `quantity_factory`, not a private `_PA_PER` table.

### 🟡 F-11 — Split-brain Pint setup
**Where:** `pump/utilities/unit_conversion.py:66-68`
**What:** the module builds `ureg = UnitRegistry()` (used to parse `STANDARD_UNITS`) but exports `Q_ = pint.Quantity`, which binds to Pint's *application* registry. It works because only dimensionality strings cross the boundary — but `ureg.formatter.default_format = '~P'` therefore never affects user-created quantities, and any future cross-registry arithmetic will raise.
**Action:** one registry: `Q_ = ureg.Quantity` and `pint.set_application_registry(ureg)`. (This is the durable fix behind ADR-0002.)

### 🟡 F-12 — O(categories) unit parsing per conversion
**Where:** `pump/utilities/unit_conversion.py:152-165`
**What:** every `quantity_factory` call loops all `STANDARD_UNITS` entries and calls `ureg(unit_map["default"])` — a string parse — per category, and every point/fluid constructor calls it per attribute.
**Action:** precompute a `dimensionality → (category, unit_map)` dict once at import; the loop becomes a dict lookup. Measurable win once curves have dozens of points (and free with F-11).

### 🟡 F-13 — Context routing turns typos into unit changes
**Where:** `pump/utilities/unit_conversion.py:93-108` (`extract_context`)
**What:** any attribute whose first token is `delta`/`atm`/`default` silently converts to a different unit (`delta_pressure` → bar). CLAUDE.md documents the convention, but nothing *rejects* an unknown intent — `delta_head` would route through the `delta` context without complaint.
**Action:** log (or warn once) when context routing fires, and consider an explicit `context=` override on `BasePoint`/`Fluid` kwargs as the schema work of ADR-0006 lands.

### 🟡 F-14 — Three gravities
**Where:** `pump/point.py:99` and `:313` (`Q_(9.81, "m/s**2")` twice), `pumpflow/binding.py:59` (`G = 9.81`)
**Action:** a single `pump.constants` (or `utilities`) value — and decide deliberately between 9.81 and standard gravity 9.80665 (≈0.03% head difference; worth a one-line ADR note since it touches acceptance numbers).

### 🟡 F-15 — Report generator side effects
**Where:** `pump/utilities/report.py:42` (`locale.setlocale(LC_ALL, '')` per construction), `:44` and `:166` (`print` in library code), `:139-145` (default filename is date-granular — two runs the same day overwrite each other; also `TAGS.replace("/", "")` is the only sanitization).
**Action:** drop `setlocale` (gettext doesn't need it here), replace prints with `logging`, add time-of-day to the default filename, and sanitize the tag with a small allowlist. Keep `generate_report` pure with respect to global state.

### 🟡 F-16 — User-facing strings
**Where:** `pump/performance_curve.py:279` ("Head Shuttoff"), `:564` ("Hydralic Power"), `:2` ("peroformance_curve")
**Action:** fix and grep for consumers — these strings are dict keys and table headers that flow into `.docx` reports and both gettext catalogs (`pt` needs recompilation per CLAUDE.md).

### 🟡 F-17 — Hygiene
**Where:** `pump/performance_curve.py:492-495` (commented-out attribute-copy block in `to_speed` — delete or resolve; it hides a real open question about which attributes should survive the transform), `pump/point.py:283` (`summary()` both prints and returns; printing belongs to the caller).

### 🟡 F-18 — Delivery gap
**What:** no `.github/workflows` — the (green) suite runs only when someone remembers; `black` is the only quality gate and nothing enforces it. The wheel packages `pumpflow`, but a plain `pip install centrifugal-pump` cannot `import pumpflow` (PySide6 is in the optional `gui` extra) — ADR-0010 territory.
**Action:** a minimal CI (pytest + `black --check` on 3.12) is a half-day and protects every refactor above; add a lazy/guarded import or an import-time error message pointing to `pip install "centrifugal-pump[gui]"`.

---

## 3. Next-generation options

Four directions, deliberately separable. Effort is relative to an 8-hour-sprint cadence (docs/sprints).

### Option A — Harden the core (recommended first)
Execute the fix list above plus the existing ADR sequence (0002 → 0001 → 0004/0005 → 0006/0007). The defining move: make `PerformanceChecker` the **single acceptance model** (one deviation definition, one tolerance table, extrapolation flags) that binding, plots, and reports all read from.
- **Effort:** ~3–4 sprints. **Risk:** low (test net exists). **Payoff:** every other option becomes safe to build.

### Option B — Headless-first FAT pipeline (`pump-cli`)
A console entry point: ingest test logs (CSV/JSON) → correct to rated speed/fluid → compliance verdict → artifacts (`.docx` today; JSON summary next, PDF/HTML per roadmap). The workbench becomes *one* client of the same pipeline; FAT campaigns become scriptable and CI-runnable on the test bench.
- **Effort:** ~2 sprints after A (the pipeline already exists inside `binding.correct_curve`/`check_compliance` — F-10's promotion work creates it for free). **Risk:** low. **Payoff:** highest utility-per-hour; unlocks batch/regression use cases no GUI can serve.

### Option C — Physics expansion (parallel track)
The roadmap gaps, in dependency order: viscosity correction (HI 9.6.7 / ISO/TR 17766 — extend `STANDARD_UNITS` with kinematic viscosity, which today only survives via a warning suppression in `binding.make_rated_fluid`), NPSH margin, system-curve intersection, impeller trim, multi-pump compare.
- **Effort:** ~1 sprint per item. **Risk:** medium (needs reference-case validation, ideally from the notebook lineage). **Payoff:** each item is a differentiating feature for the FAT audience (UC registry).

### Option D — Web workbench
FastAPI service over the Option-B pipeline + browser node canvas; multi-user, no PySide6 install. The signal layer (`signals.py` frozen dataclasses) and `persistence.py`'s plain-magnitude JSON are already the right wire format.
- **Effort:** large (multi-month). **Risk:** high. **Payoff:** real, but only after A+B exist — do not start here.

**Recommended sequencing:** **A → B**, with **C** items interleaved as sprint-sized deliverables; revisit **D** once B has users. Each option, when accepted, should be registered as ADR-0011+ per the append-only convention.

---

## 4. Suggested first sprint (if Option A is accepted)

1. F-08, F-16, F-17 — one-liners, zero risk, land with tests.
2. F-01 + F-02 — the two crash/credibility fixes in `PerformanceChecker`, with the boundary tests from F-05.
3. F-18 CI — so everything after runs under a net.

*Review performed by Claude Code (Fable 5); findings verified against source at the lines cited. No code was modified.*
