# Sprint S7 — Quick single-point head check (8 h)

- **Goal:** A user can compute head (and the obvious derived quantities) for ONE
  operating point — in Python via `pump.TestPoint`, and in the workbench via a new
  standalone **Quick Point Calculator** node — with no curve fit, correction,
  compliance, or report.
- **Persona / UC:** application engineer · student-learner · UC-11.
- **Branch / commit:** `s7-quick-point` — one commit.

> **For the implementing loop agent — read first.**
> - **One task per iteration.** After every task run `pytest` and `black .`; only
>   move on when both are green. Never edit two areas in one iteration.
> - **`pytest` does NOT collect `pumpflow/`** (it needs PySide6). The pinning test
>   (T2) therefore targets the **`pump` library**, which always runs. Do not put
>   assertions inside `pumpflow/`.
> - **Always pass `Q_(...)` quantities** into library constructors — never bare
>   numbers (raises `ValueError`).
> - **Do not invent numbers** — use the worked case below exactly.
> - **Do not touch** `pump/performance_curve.py`, `binding.correct_curve`, or
>   `app.build_default_pipeline`. The new node is on-demand, not default wiring.
> - If a task's verify command fails, fix *that task* before continuing.

## Worked numeric case (use these exact values in the test)

Inputs: ρ = 1000 kg/m³, Q = 360 m³/h, p_suction = 1.0 bar,
p_discharge = 5.905 bar, breaking_power = 60 kW, no diameters, no elevation.

Then Δp = 4.905 bar = 490 500 Pa and:

| quantity | expected |
|----------|----------|
| head | 50.0 m |
| pressure_head | 50.0 m |
| velocity_head | 0 m |
| elevation_head | 0 m |
| specific energy g·H | 490.5 J/kg |
| hydraulic_power (ρ·Q·g·H) | 49.05 kW |
| efficiency (Pₕ/P_brake) | 81.75 % |

Formulas: H = Δp/(ρg); Pₕ = ρ·(Q/3600)·g·H; η = Pₕ/P_brake; g = 9.81 m/s².
Assert with `pytest.approx(rel=1e-3)`.

## Tasks (≈ 8 h) — do in order, one per iteration

- [ ] **T1 — Library doctest** — ~1h. In [`pump/point.py`](../../pump/point.py)
  extend the `TestPoint` class docstring (the example block near the class top) with
  a runnable doctest that builds a point from `inlet_pressure`/`outlet_pressure` +
  density and shows `head`, `pressure_head`, `hydraulic_power`, and `efficiency`
  (supply `breaking_power`). Verify: `pytest --doctest-modules pump/point.py`.
- [ ] **T2 — Pinning test** — ~1.5h. Create `tests/test_quick_point.py` for the
  worked case: build `Fluid` + `TestPoint` with `Q_`, assert head, the three head
  components, specific energy (`(tp.head * tp.g)` in J/kg), hydraulic power, and
  efficiency to `rel=1e-3`. Mirror imports/fixtures in
  [`tests/conftest.py`](../../tests/conftest.py).
  Verify: `pytest tests/test_quick_point.py -q`.
- [ ] **T3 — Signal** — ~0.5h. Add a frozen `PointResult` dataclass to
  [`pumpflow/signals.py`](../../pumpflow/signals.py) with plain-float fields:
  `tag, q_m3h, head_m, pressure_head_m, velocity_head_m, elevation_head_m,
  specific_energy_jkg, hydraulic_power_kw, efficiency_pct (Optional[float])`.
  Verify: `python -c "import pumpflow.signals"`.
- [ ] **T4 — Binding** — ~1.5h. Add `compute_point(...) -> PointResult` to
  [`pumpflow/binding.py`](../../pumpflow/binding.py) — the ONLY place that calls
  `pump`. Wrap magnitudes in `Q_`, build `Fluid` + `TestPoint`, read properties,
  return a `PointResult`. Raise `BindingError` on density ≤ 0 or
  p_discharge ≤ p_suction; efficiency is `None` when no breaking power. (Skeleton
  below.) Verify: `python -c "from pumpflow.binding import compute_point"` plus a
  one-liner that prints `compute_point(...)` for the worked case → head ≈ 50.0.
- [ ] **T5 — Node** — ~2.5h. Create `pumpflow/nodes/quick_point.py` with
  `QuickPointNode` (source node + dialog), modeled on
  [`pumpflow/nodes/correction.py`](../../pumpflow/nodes/correction.py). Register it
  in [`pumpflow/nodes/registry.py`](../../pumpflow/nodes/registry.py) `_CLASSES`.
  (Skeleton below.) Verify:
  `python -c "from pumpflow.nodes.registry import make_node; print(make_node('quick_point').title)"`.
- [ ] **T6 — Docs** — ~1h. Add **UC-11** to
  [`docs/product/use-cases.md`](../product/use-cases.md) (MVP section, exact
  template) + a priority-summary line; add a one-line persona note to
  [`docs/product/audience.md`](../product/audience.md); tick this sprint in
  [`docs/sprints/README.md`](README.md). Verify: links resolve; `pytest` still green.

## Files touched

- Create: `tests/test_quick_point.py`, `pumpflow/nodes/quick_point.py`.
- Modify: `pump/point.py`, `pumpflow/signals.py`, `pumpflow/binding.py`,
  `pumpflow/nodes/registry.py`, `docs/product/use-cases.md`,
  `docs/product/audience.md`, `docs/sprints/README.md`.

## Acceptance criteria

- `pytest` green (incl. the new doctest + `tests/test_quick_point.py`); `black .` clean.
- `make_node("quick_point")` returns the node; it shows in the workbench Add-node
  menu and is NOT in the default pipeline.
- For the worked case, both `compute_point` and the node's result panel report
  head = 50.0 m, hydraulic power = 49.05 kW, efficiency = 81.75 %.

## Definition of Done

- [ ] All tasks checked, tests green, `black` clean, one commit on `s7-quick-point`.

## Code skeletons (fill in; match the style of neighbouring code)

```python
# --- pumpflow/binding.py : compute_point -----------------------------------
def compute_point(q_m3h, p_suction, p_discharge, density_kgm3, pressure_unit="bar",
                  inlet_diameter_mm=None, outlet_diameter_mm=None,
                  breaking_power_kw=None, tag="point") -> PointResult:
    if density_kgm3 <= 0:
        raise BindingError("Density must be > 0.")
    if p_discharge <= p_suction:
        raise BindingError("Discharge pressure must exceed suction pressure.")
    fluid = Fluid("Test fluid", density=Q_(density_kgm3, "kg/m**3"))
    kw = dict(fluid=fluid, capacity=Q_(q_m3h, "m**3/h"),
              inlet_pressure=Q_(p_suction, pressure_unit),
              outlet_pressure=Q_(p_discharge, pressure_unit))
    if inlet_diameter_mm and outlet_diameter_mm:
        kw["inlet_diameter"] = Q_(inlet_diameter_mm, "mm")
        kw["outlet_diameter"] = Q_(outlet_diameter_mm, "mm")
    if breaking_power_kw:
        kw["breaking_power"] = Q_(breaking_power_kw, "kW")
    tp = TestPoint(**kw)
    eff = tp.efficiency.to("percent").magnitude if breaking_power_kw else None
    return PointResult(
        tag=tag, q_m3h=q_m3h, head_m=tp.head.to("m").magnitude,
        pressure_head_m=tp.pressure_head.to("m").magnitude,
        velocity_head_m=tp.velocity_head.to("m").magnitude,
        elevation_head_m=tp.elevation_head.to("m").magnitude,
        specific_energy_jkg=(tp.head * tp.g).to("J/kg").magnitude,
        hydraulic_power_kw=tp.hydraulic_power.to("kW").magnitude,
        efficiency_pct=eff,
    )


# --- pumpflow/nodes/quick_point.py : QuickPointNode -------------------------
class QuickPointNode(BaseNode):
    kind = "quick_point"
    title = "Quick Point Calculator"
    glyph = "≈"
    is_source = True
    inputs = []
    outputs = [PortSpec("PointResult", "PointResult")]

    def default_settings(self):
        return {"q_m3h": 360.0, "p_suction": 1.0, "p_discharge": 5.905,
                "density_kgm3": 1000.0, "pressure_unit": "bar",
                "use_diameters": False, "inlet_diameter_mm": 200.0,
                "outlet_diameter_mm": 150.0,
                "use_power": True, "breaking_power_kw": 60.0, "tag": "point"}

    def compute(self, inputs):
        s = self.settings
        try:
            res = compute_point(
                s["q_m3h"], s["p_suction"], s["p_discharge"], s["density_kgm3"],
                pressure_unit=s["pressure_unit"],
                inlet_diameter_mm=s["inlet_diameter_mm"] if s["use_diameters"] else None,
                outlet_diameter_mm=s["outlet_diameter_mm"] if s["use_diameters"] else None,
                breaking_power_kw=s["breaking_power_kw"] if s["use_power"] else None,
                tag=s["tag"])
        except BindingError as exc:
            return self.emit_nothing(str(exc), "invalid")
        self._last = res
        self.status = f"H = {res.head_m:.1f} m · Pₕ = {res.hydraulic_power_kw:.1f} kW"
        self.state = "ok"
        return {"PointResult": res}

    # create_dialog: build input rows with the `ui` helpers used in correction.py
    # (ui.spin / ui.checkbox / ui.row / ui.section) for Q, p_suction, p_discharge,
    # density, pressure unit, the optional diameters and breaking-power toggles;
    # below them a read-only results panel (ui.section + labels/grid) showing head,
    # the three components, specific energy, hydraulic power, efficiency. Recompute
    # the panel on every change via on_change(), like correction.py's refresh().
```

## Verification (whole sprint, end-to-end)

1. `pytest` and `pytest --doctest-modules pump` green; `black .` clean.
2. By hand: H = (5.905 − 1.0) bar / (1000 · 9.81) = 50.0 m — matches the test.
3. `python -m pumpflow` → Add node → **Quick Point Calculator** → enter the worked
   case → result panel shows head 50.0 m, hydraulic power 49.05 kW, efficiency
   81.75 %; toggling diameters on changes the velocity-head term; clearing breaking
   power hides efficiency.
4. Save/reload a `.pumpflow` containing the node → inputs round-trip.
