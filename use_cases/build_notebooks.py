"""Generate the worked use-case notebooks of sprint 13.

Every notebook is written with ``nbformat`` (v4) from plain Python strings, so the
sources stay reviewable.  Run from anywhere::

    python use_cases/build_notebooks.py

The notebooks are written next to this script (``use_cases/``).  They are written
*unexecuted*; execute them with ``jupyter nbconvert --execute --inplace`` or let
``pytest tests/test_notebooks.py`` run them.  Edit this script (not the .ipynb) and
re-run it to change a notebook.

Convention (see ``use_cases/README.md``): public ``pump`` API only, Pint quantities
in the engineer's units, and final cells that ``assert`` the result.
"""

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

HERE = Path(__file__).resolve().parent


def md(text):
    return new_markdown_cell(text.strip("\n"))


def code(text):
    return new_code_cell(text.strip("\n"))


def write(name, cells):
    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python"}
    nbformat.validate(nb)
    path = HERE / f"{name}.ipynb"
    nbformat.write(nb, path)
    return path


# --------------------------------------------------------------------------- #
# Shared cell sources
# --------------------------------------------------------------------------- #
COMMON_SETUP = r"""
import warnings

import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Image, display

from pump import Q_, Fluid, Water, TestPoint, PerformanceCurve
"""

# P-1001A water test (the data of UC-06 / examples/catalogue): Q, Head, P, eta.
P1001A_DATA = r"""
# Illustrative water test of pump P-1001A (1480 rpm):
#          Q [m3/h]  Head [m]  P [kW]  eta [%]
P1001A = [
    (160.0, 125.37, 77.97, 70.03),
    (240.0, 119.11, 95.17, 81.82),
    (320.0, 110.79, 114.44, 84.44),
    (400.0, 100.01, 147.26, 74.00),
    (480.0, 86.72, 173.98, 65.13),
    (540.0, 75.60, 194.76, 57.14),
]
water = Fluid("Test water", density=Q_(1000.0, "kg/m**3"))


def build_curve(rows, fluid, speed, degree=3, head_k=1.0, power_k=1.0, eff_k=1.0):
    "Measured rows -> PerformanceCurve with Head / eta pinned on the points."
    points = [
        TestPoint(
            fluid=fluid,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=speed,
            _head=Q_(h * head_k, "m"),
            _efficiency=Q_(e * eff_k, "percent"),
            breaking_power=Q_(p * power_k, "kW"),
        )
        for q, h, p, e in rows
    ]
    return PerformanceCurve(fluid, points, polynomial_degree=degree)
"""


# --------------------------------------------------------------------------- #
# UC-01 Selection
# --------------------------------------------------------------------------- #
def uc01():
    return [
        md(r"""
# UC-01 · Select a pump for given conditions

**Use case:** [UC-01](../docs/product/use-cases.md) - *given a duty (Q, H) and a
catalogue of known pump curves, rank the pumps that can serve it, as they are, with
a speed change (VFD) or with an impeller trim.*

The catalogue is a folder of `*.pumpcurve.json` files (value + unit pairs).  This
notebook builds three small curves, writes them to a temporary folder, loads them
with `Catalogue.from_folder` and calls `Catalogue.select`.  Ranking: pumps inside the
preferred operating region (POR) first, then higher efficiency at the duty, then the
smaller distance from the best-efficiency point.

> The POR (70-120 % of the BEP flow) comes from a secondary source and is flagged
> `verified = false`.  Viscosity correction is **not** applied by the selection.

**Acceptance:** every candidate passes through the duty head at the duty flow (1 %
for an as-is curve, exactly for speed / trim); the ranking order is respected; a
pump that cannot reach the duty is rejected with a reason.
"""),
        md("## 1 · Setup"),
        code(COMMON_SETUP + r"""
import tempfile
from pathlib import Path

from pump import AcceptanceCriteria, Catalogue, CatalogueEntry
from pump.catalogue import load_entry, save_entry
"""),
        md(r"""
## 2 · Three catalogue curves

Each entry carries the curve, the speed and impeller diameter it was measured at, and
the allowed diameter range.  `P-1002A` is a larger pump (flow x 1.3, head x 0.85) and
`P-0500S` a small one that cannot reach the duty.
"""),
        code(P1001A_DATA + r"""

def make_entry(name, speed, diameter, d_min, d_max, q_scale=1.0, h_scale=1.0):
    rows = [(q * q_scale, h * h_scale, p * q_scale * h_scale, e) for q, h, p, e in P1001A]
    return CatalogueEntry(
        name=name,
        curve=build_curve(rows, water, speed),
        speed=speed,
        diameter=diameter,
        d_min=d_min,
        d_max=d_max,
    )


rpm = Q_(1480, "rpm")
entries = [
    make_entry("P-1001A", rpm, Q_(300, "mm"), Q_(270, "mm"), Q_(310, "mm")),
    make_entry("P-1002A", rpm, Q_(340, "mm"), Q_(300, "mm"), Q_(350, "mm"), 1.3, 0.85),
    make_entry("P-0500S", rpm, Q_(180, "mm"), Q_(160, "mm"), Q_(190, "mm"), 0.2, 1.0),
]
for e in entries:
    print(e.name, e.speed, e.diameter, "has efficiency:", e.has_efficiency)
"""),
        md(r"""
## 3 · Write and load the catalogue

`save_entry` writes one `*.pumpcurve.json` per pump; `Catalogue.from_folder` reads the
folder back.  A malformed file never aborts the load: it is listed in `load_errors`.
"""),
        code(r"""
tmp = tempfile.TemporaryDirectory()
catalogue_dir = Path(tmp.name)
for e in entries:
    save_entry(e, catalogue_dir)

catalogue = Catalogue.from_folder(catalogue_dir)
print("files    :", sorted(p.name for p in catalogue_dir.glob("*.pumpcurve.json")))
print("entries  :", catalogue.names)
print("errors   :", catalogue.load_errors)

reloaded = load_entry(catalogue_dir / "P-1001A.pumpcurve.json")
print("round trip speed:", reloaded.speed, "| diameter:", reloaded.diameter)
"""),
        md(r"""
## 4 · Select for a duty

Duty: 300 m3/h at 105 m of differential head, the user's engineering units
(here 1321 gpm and 344 ft would give the same result).
"""),
        code(r"""
duty_q = Q_(300.0, "m**3/h")
duty_h = Q_(105.0, "m")

ranked = catalogue.select(duty_q, duty_h)

print(f"{'#':>2} {'candidate':<26} {'how':<7} {'eta %':>6} {'P kW':>7} {'Q/Qbep':>7} {'POR':>4}")
for i, c in enumerate(ranked, start=1):
    power = c.power_at_duty.magnitude if c.power_at_duty is not None else float("nan")
    print(
        f"{i:>2} {c.label:<26} {c.adaptation:<7} {c.eta_at_duty.magnitude:6.1f} "
        f"{power:7.1f} {c.q_over_qbep:7.2f} {str(c.in_por):>4}"
    )

print("\nRejected:")
for reason in ranked.reasons:
    print(" -", reason[:140])
"""),
        md(r"""
## 5 · Plot the best candidates

The adapted head curves of the three best candidates all pass through the duty point.
"""),
        code(r"""
fig, ax = plt.subplots(figsize=(7, 4.5))
for c in ranked[:3]:
    caps = np.asarray(c.curve.fitter.capacities, dtype=float)
    xs = np.linspace(caps.min(), caps.max(), 200)
    ax.plot(xs, np.polyval(c.curve.fitter.head_coeffs, xs), label=c.label)
ax.plot(duty_q.magnitude, duty_h.magnitude, "k*", ms=14, label="duty")
ax.set_xlabel("Capacity (m3/h)")
ax.set_ylabel("Head (m)")
ax.set_title("UC-01 - candidates adapted to the duty")
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 6 · The preferred operating region

The POR bounds are data (`AcceptanceCriteria.selection`), not code.
"""),
        code(r"""
crit = AcceptanceCriteria.default()
sel = crit.selection
print(f"POR = [{sel.por_min:g}, {sel.por_max:g}] x Q_BEP  | verified = {sel.verified}")
print("source:", sel.source[:110], "...")
"""),
        md(r"""
## 7 · Acceptance

Final assertions: the demo becomes a test.
"""),
        code(r"""
# the catalogue loaded all three files
assert catalogue.names == ["P-0500S", "P-1001A", "P-1002A"]
assert catalogue.load_errors == []
assert reloaded.speed.to("rpm").magnitude == 1480

# at least two pumps can serve the duty
assert len(ranked) >= 2

# every candidate passes through the duty head at the duty flow
for c in ranked:
    h = c.curve.predict_head(duty_q).to("m").magnitude
    assert abs(h - duty_h.magnitude) / duty_h.magnitude < 0.01, (c.label, h)
    assert c.adaptation in ("as-is", "speed", "trim")
    if c.adaptation == "speed":
        assert 0.9 * 1480 < c.value.to("rpm").magnitude < 1.1 * 1480
    if c.adaptation == "trim":
        assert c.entry.d_min <= c.value <= c.entry.d_max

# ranking: in-POR candidates first, then non-increasing efficiency
for a, b in zip(ranked, ranked[1:]):
    assert a.in_por or not b.in_por
    if a.in_por == b.in_por:
        assert a.eta_at_duty.magnitude >= b.eta_at_duty.magnitude - 1e-3

# the small pump cannot reach the duty and says why
assert "P-0500S" in {r.name for r in ranked.rejected}
assert all("P-0500S" != c.name for c in ranked)

# the catalogue entries are not mutated by the selection
assert catalogue.entries[1].speed.to("rpm").magnitude == 1480
assert sel.verified is True  # API 610 12th ed.: POR 70-120 % of BEP, checked

tmp.cleanup()
print("UC-01 acceptance OK:", [c.label for c in ranked[:3]])
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-02 Performance verification (P-9001A, native Vendor A units)
# --------------------------------------------------------------------------- #
def uc02():
    return [
        md(r"""
# UC-02 · Verify pump performance (FAT) - P-9001A in native units

**Use case:** [UC-02](../docs/product/use-cases.md) - *rated nameplate + measured
test points -> fitted H-Q / P-Q / eta-Q curves, deviation vs rated, pass / fail
verdict.*

The data is the Vendor A test sheet of pump **P-9001A**, entered **exactly as
printed**: flow in gpm, differential pressure in psi, water temperature in degF, motor
output in hp and the pump speed in rpm.  There is no hand conversion: Pint carries the
units and the library normalises them.

Steps: head and efficiency per row (with the water density at each row's
temperature) -> pin them on `TestPoint`s -> `to_speed` (10 301 -> 10 212 rpm) ->
`to_fluid` (test water -> rated fluid, SG 0.999) -> degree-3 fit -> `PerformanceChecker`
against **API 610 8th edition + client overlay N-553**.

> The API 610 8th-edition tolerances (Table 4-2) and the N-553 rev E overlay were
> checked against the standard texts; see
> [acceptance tolerances](../docs/concepts/acceptance-tolerances.md).  Efficiency is
> **not a rated value** in API 610, so it is reported for information only.

**Acceptance:** at the rated flow 9.80 m3/h the predicted head is about 339.5 m
(+1.7 % vs 333.8 m, inside +/-2 %), power about 24.6 kW and efficiency about 36.8 %.
"""),
        md("## 1 · Setup"),
        code(r"""
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Image, display

from pump import (
    AcceptanceCriteria,
    DesignPoint,
    Fluid,
    PerformanceChecker,
    PerformanceCurve,
    Q_,
    TestPoint,
    Water,
    deviation,
)
from pump.constants import G
"""),
        md(r"""
## 2 · The test sheet, as printed

One row per test point: flow [gpm], differential pressure [psi], water temperature
[degF], motor output [hp].  The pump speed is a single reading.
"""),
        code(r"""
sheet = [
    # gpm,  dP psi,  T degF,  motor hp
    (15.2, 524.7, 130, 25.41),
    (29.4, 522.1, 129, 28.83),
    (34.8, 513.4, 129, 30.56),
    (43.5, 486.5, 127, 33.36),
    (47.9, 459.5, 126, 35.09),
    (52.2, 431.7, 126, 36.61),
]
pump_speed = Q_(10301, "rpm")

rated = dict(
    q=Q_(9.80, "m**3/h"),
    head=Q_(333.8, "m"),
    speed=Q_(10212, "rpm"),
    power=Q_(26.9, "kW"),
    efficiency=Q_(32.7, "percent"),
)
rated_fluid = Fluid("Wash water (rated)", density=Q_(999.0, "kg/m**3"))  # SG 0.999
print("rated:", {k: f"{v:~P}" for k, v in rated.items()})
"""),
        md(r"""
## 3 · Head and efficiency per row

Each row is evaluated with **its own** water density (temperature dependent):
`TestPoint.head` is the pressure head `dP / (rho g)` and `TestPoint.efficiency` is the
hydraulic power over the breaking (motor output) power.
"""),
        code(r"""
rows = []
print(f"{'Q gpm':>6} {'Q m3/h':>7} {'rho kg/m3':>9} {'Head m':>8} {'P kW':>7} {'eta %':>6}")
for gpm, dp, t_f, hp in sheet:
    rho = Water(Q_(t_f, "degF")).density
    tp = TestPoint(
        fluid=Fluid("row water", density=rho),
        capacity=Q_(gpm, "gallon/min"),
        delta_pressure=Q_(dp, "psi"),
        breaking_power=Q_(hp, "hp"),
    )
    rows.append((rho, tp))
    print(
        f"{gpm:6.1f} {tp.capacity.magnitude:7.2f} {rho.magnitude:9.1f} "
        f"{tp.head.to('m').magnitude:8.2f} {tp.breaking_power.to('kW').magnitude:7.2f} "
        f"{tp.efficiency.to('percent').magnitude:6.1f}"
    )

# hand check of the first row with Pint: head = dP / (rho g)
rho0, tp0 = rows[0]
hand = (Q_(sheet[0][1], "psi") / (rho0 * G)).to("m")
print(f"\nrow 1 by hand: {hand:.3f~P}  | library: {tp0.head.to('m'):.3f~P}")
"""),
        md(r"""
### The complete head (pressure + velocity + elevation)

When the bench geometry is known, `TestPoint` adds the velocity and elevation heads.
Here row 3 gets illustrative pipe IDs and gauge elevations: the total head is the sum
of the three components.
"""),
        code(r"""
rho3, tp3 = rows[2]
geo = TestPoint(
    fluid=Fluid("row water", density=rho3),
    capacity=tp3.capacity,
    delta_pressure=Q_(sheet[2][1], "psi"),
    inlet_diameter=Q_(2.0, "inch"),
    outlet_diameter=Q_(1.0, "inch"),
    inlet_elevation=Q_(0.3, "m"),
    outlet_elevation=Q_(0.8, "m"),
)
parts = {
    "pressure": geo.pressure_head.to("m"),
    "velocity": geo.velocity_head.to("m"),
    "elevation": geo.elevation_head.to("m"),
}
for name, value in parts.items():
    print(f"{name:>10}: {value:.4f~P}")
print(f"{'total':>10}: {geo.compute_head.to('m'):.4f~P}")
"""),
        md(r"""
## 4 · Speed and density correction, then the fit

The measured points are pinned (`_head`, `_efficiency`) on a curve whose single fluid
is the mean test water (just a label, since Head and eta are pinned).  Then the
curve is corrected to the rated speed with the affinity laws and to the rated fluid.
Both transforms return **new** curves.
"""),
        code(r"""
rho_mean = Q_(float(np.mean([r.to("kg/m**3").magnitude for r, _ in rows])), "kg/m**3")
test_water = Fluid("Test water (mean)", density=rho_mean)

pinned = [
    TestPoint(
        fluid=test_water,
        capacity=tp.capacity,
        speed_of_rotation=pump_speed,
        _head=tp.head,
        _efficiency=tp.efficiency,
        breaking_power=tp.breaking_power,
    )
    for _, tp in rows
]
measured = PerformanceCurve(test_water, pinned, polynomial_degree=3)
speed_corrected = measured.to_speed(rated["speed"])
corrected = speed_corrected.to_fluid(rated_fluid)

print(f"{'Q_corr m3/h':>12} {'H_corr m':>9} {'P_corr kW':>10} {'eta %':>6}")
for p in corrected.points:
    print(
        f"{p.capacity.to('m**3/h').magnitude:12.3f} {p.head.to('m').magnitude:9.2f} "
        f"{p.breaking_power.to('kW').magnitude:10.2f} {p.efficiency.to('percent').magnitude:6.2f}"
    )
"""),
        md(r"""
## 5 · Check against the rated point

`AcceptanceCriteria.load("api610:8", client="n553")` selects the edition and the client
overlay.  API 610 8th ed. Table 4-2: the rated head 333.8 m is above 300 m, so the head
band is -2/+2 %, the shut-off band +/-5 % and the power limit +4 %.  The N-553 rev E
overlay adds the NPSH margin rule (>= 0.8 m and NPSHa/NPSHr >= 1.15 at rated flow).
"""),
        code(r"""
criteria = AcceptanceCriteria.load("api610:8", client="n553")
design = DesignPoint(
    fluid=rated_fluid,
    capacity=rated["q"],
    differential_head=rated["head"],
    breaking_power=rated["power"],
)
checker = PerformanceChecker(design, corrected, criteria=criteria)

print(criteria.label, "+", criteria.client_label, "| verified:", criteria.verified)
print("unverified parts:", ", ".join(criteria.unverified))
print()
print(checker.check_summary)
print()
print({k: f"{v:~P}" for k, v in checker.acceptable_limits.items()})
"""),
        md(r"""
## 6 · The corrected curves
"""),
        code(r"""
png = corrected.plot_performance_curve(
    chart_title="P-9001A - corrected to 10212 rpm, SG 0.999",
    capacity=rated["q"],
    return_io=True,
)
display(Image(data=png.getvalue()))
"""),
        md(r"""
## 7 · Acceptance

The numbers below are the project's regression fixture (sprint 1-3 changelog).
"""),
        code(r"""
pred_h = corrected.predict_head(rated["q"]).to("m")
pred_p = corrected.predict_breaking_power(rated["q"]).to("kW")
pred_e = corrected.predict_efficiency(rated["q"]).to("percent")
dev_h = deviation(rated["head"], pred_h)
print(f"H = {pred_h:.2f~P}  P = {pred_p:.2f~P}  eta = {pred_e:.2f~P}  dH = {dev_h:+.2%}")

# the head per row is dP/(rho g): the library equals the hand computation
assert abs((hand - tp0.head).to("m").magnitude) < 1e-9

# the complete head is the sum of its three components
total = parts["pressure"] + parts["velocity"] + parts["elevation"]
assert abs((total - geo.compute_head).to("m").magnitude) < 1e-9
assert parts["velocity"].magnitude > 0 and abs(parts["elevation"].magnitude - 0.5) < 1e-9

# affinity: capacity scales with the speed ratio
ratio = 10212 / 10301
assert abs(corrected.points[0].capacity.magnitude - measured.points[0].capacity.magnitude * ratio) < 1e-9

# predicted values at the rated flow (regression fixture)
assert abs(pred_h.magnitude - 339.55) < 0.6
assert abs(pred_p.magnitude - 24.60) < 0.35
assert abs(pred_e.magnitude - 36.80) < 0.5
assert 0.015 < dev_h < 0.019

# verdict: inside +/-2 % head, power below +4 %
assert checker.minimum_head <= pred_h <= checker.maximum_head
assert pred_p <= checker.maximum_breaking_power
assert "False" not in checker.check_summary

# the performance tolerances are checked against API 610 8th ed. Table 4-2;
# only the mechanical-run limits remain open (no run test in the 8th edition)
assert criteria.verified is True
assert criteria.performance_unverified == ()
assert criteria.efficiency_tol_minus is None  # "Efficiency is not a rating value"
print("UC-02 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-03/UC-04 System curve + operating point
# --------------------------------------------------------------------------- #
def uc0304():
    return [
        md(r"""
# UC-03 / UC-04 · System curve and operating point

**Use cases:** [UC-03 and UC-04](../docs/product/use-cases.md) - *describe the
piping system by a resistance curve, then find where the pump curve meets it.*

Two system models share the same interface (`head(q)`):

- `SystemCurve` - $H = H_{static} + k\,Q^n$, from `k` or from two points;
- `PipeSystemCurve` (built with `SystemCurve.from_pipe`) - Darcy-Weisbach with Swamee-Jain
  friction and minor losses, evaluated at every flow.

`pump.operating_point.operating_point` brackets the first sign change of
$H_{pump}(Q) - H_{system}(Q)$ and refines it by bisection.  The pump head is the
fitted polynomial (`method="poly"`) or a natural cubic spline (`"spline"`).

**Acceptance:** at the operating point both heads agree; a solution inside the tested
range is not flagged as extrapolated; a system that never meets the pump raises.
"""),
        md("## 1 · Setup and the pump curve"),
        code(COMMON_SETUP + P1001A_DATA + r"""
from pump import PipeSystemCurve, SystemCurve
from pump.operating_point import operating_point

curve = build_curve(P1001A, water, Q_(1480, "rpm"))
print("tested range:", min(curve.fitter.capacities), "-", max(curve.fitter.capacities), "m3/h")
"""),
        md(r"""
## 2 · A system curve from two points

Static head and `k` follow from two (Q, H) points: here 25 m at 100 m3/h and 60 m at
400 m3/h.  `k` is stored in `m / (m3/h)**n`, but any equivalent unit is accepted.
"""),
        code(r"""
sc = SystemCurve.from_points(
    (Q_(100, "m**3/h"), Q_(25, "m")), (Q_(400, "m**3/h"), Q_(60, "m"))
)
print("static head:", sc.static_head, "| k:", sc.k, "| n =", sc.exponent)

# same system expressed in imperial units (static head in ft, k in ft/gpm**2)
k_us = sc.k.to("ft/(gallon/minute)**2")
sc_us = SystemCurve(sc.static_head.to("ft"), k_us)
print("static in ft:", sc.static_head.to("ft"), "| k in ft/gpm**2:", k_us)
"""),
        md(r"""
## 3 · Operating point on the pump curve
"""),
        code(r"""
op = operating_point(curve, sc)
print(f"Q = {op.q:.1f~P}  H = {op.h:.2f~P}  P = {op.power:.1f~P}  eta = {op.efficiency:.1f~P}")
print("extrapolated:", op.extrapolated)

op_spline = operating_point(curve, sc, method="spline")
print(f"spline: Q = {op_spline.q:.1f~P}  H = {op_spline.h:.2f~P}")
"""),
        code(r"""
qs = Q_(np.linspace(0.0, 600.0, 241), "m**3/h")
tested = np.asarray(curve.fitter.capacities, dtype=float)
xs = np.linspace(tested.min(), tested.max(), 200)

fig, ax = plt.subplots(figsize=(7, 4.5))
ax.plot(xs, np.polyval(curve.fitter.head_coeffs, xs), label="pump (poly fit)")
ax.plot(qs.magnitude, sc.head(qs).magnitude, label="system H = Hs + k Q^2")
ax.plot(op.q.magnitude, op.h.magnitude, "k*", ms=14, label="operating point")
ax.set_xlabel("Capacity (m3/h)")
ax.set_ylabel("Head (m)")
ax.set_ylim(0, 140)
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 4 · A pipe run with Darcy-Weisbach friction

1500 m of 200 mm steel pipe (roughness 0.045 mm), 20 m of static head and a sum of
minor-loss coefficients of 20, carrying 20 degC water.  The friction factor is
Swamee-Jain for turbulent flow (and 64/Re for Re < 2300).
"""),
        code(r"""
pipe = SystemCurve.from_pipe(
    static_head=Q_(20, "m"),
    length=Q_(1500, "m"),
    diameter=Q_(200, "mm"),
    roughness=Q_(0.045, "mm"),
    fluid=Water(Q_(20, "degC")),
    minor_k_sum=20.0,
    q_ref=Q_(400, "m**3/h"),
)
q400 = Q_(400, "m**3/h")
print(f"Re = {float(pipe.reynolds(q400)):.3g}  f = {float(pipe.friction_factor(q400)):.4f}  "
      f"H(400 m3/h) = {pipe.head(q400):.1f~P}")

op_pipe = operating_point(curve, pipe)
print(f"pipe system: Q = {op_pipe.q:.1f~P}  H = {op_pipe.h:.2f~P}  extrapolated = {op_pipe.extrapolated}")

# the equivalent k Q^2 curve matched at the operating point finds the same intersection
eq = pipe.equivalent(op_pipe.q)
op_eq = operating_point(curve, eq)
print(f"equivalent: static = {eq.static_head:.1f~P}  k = {eq.k:.3e~P}  -> Q = {op_eq.q:.2f~P}")
"""),
        md(r"""
## 5 · A system the pump cannot serve

A static head above the pump's shut-off head never meets the curve inside the search
range, and the library says so instead of returning a number.
"""),
        code(r"""
too_high = SystemCurve(Q_(200, "m"), Q_(1e-4, "m/(m**3/h)**2"))
try:
    operating_point(curve, too_high)
    no_intersection = False
except ValueError as exc:
    no_intersection = True
    print("ValueError:", str(exc)[:120])
"""),
        md("## 6 · Acceptance"),
        code(r"""
# two-point system: exact static head and k
assert abs(sc.static_head.to("m").magnitude - 22.6667) < 1e-3
assert abs(sc.k.magnitude - 35.0 / 150000.0) < 1e-12
assert abs(sc_us.static_head.to("m").magnitude - sc.static_head.to("m").magnitude) < 1e-3
assert abs(sc_us.k.to("m/(m**3/h)**2").magnitude - sc.k.magnitude) < 1e-12

# at the operating point pump and system heads agree
pump_h = curve.predict_head(op.q).to("m").magnitude
assert abs(pump_h - sc.head(op.q).to("m").magnitude) < 1e-6
assert abs(pump_h - op.h.to("m").magnitude) < 1e-6
tested_lo, tested_hi = tested.min(), tested.max()
assert tested_lo <= op.q.to("m**3/h").magnitude <= tested_hi
assert op.extrapolated is False
assert abs(op.power.magnitude - curve.predict_breaking_power(op.q).magnitude) < 1e-9

# the spline agrees with the polynomial within a few percent
assert abs(op_spline.q.magnitude - op.q.magnitude) / op.q.magnitude < 0.05

# pipe system: heads agree and the equivalent curve gives the same flow
assert abs(curve.predict_head(op_pipe.q).magnitude - pipe.head(op_pipe.q).magnitude) < 1e-6
assert op_pipe.extrapolated is False
assert abs(op_eq.q.magnitude - op_pipe.q.magnitude) < 1e-3

# no intersection -> error
assert no_intersection
print("UC-03/04 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-05 NPSH
# --------------------------------------------------------------------------- #
def uc05():
    return [
        md(r"""
# UC-05 · Check the NPSH margin

**Use case:** [UC-05](../docs/product/use-cases.md) - *compare the NPSH available
at the suction with the NPSH required by the pump.*

$$ NPSH_a = \frac{p_{s,abs} - p_v}{\rho\,g} + \frac{v_s^2}{2g} + z_s $$

`pump.npsh` provides `npsh_available`, `npsh3_from_sweep` (3 % head drop),
`NPSHrCurve` (least-squares polynomial of NPSHr vs flow, with an extrapolation flag),
`npsh_margin` and `check_npsh` against an `NPSHCriteria` rule.

> No public margin rule was found for API 610 / N-553, so the shipped rule is **not
> configured** and the verdict is `info`.  The rule used in section 5 is an
> *illustrative demo rule*, not a standard value.

**Acceptance:** `npsh_available` equals an independent hand computation; the NPSH3
sweep interpolates to the right value; the margin verdicts follow the rule.
"""),
        md("## 1 · Setup"),
        code(r"""
import math

import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Image, display

from pump import (
    NPSHCriteria,
    NPSHrCurve,
    Pressure,
    Q_,
    Water,
    check_npsh,
    npsh3_from_sweep,
    npsh_available,
    npsh_margin,
    plot_npsh,
)
from pump.constants import G
"""),
        md(r"""
## 2 · NPSH available from the suction conditions

20 degC water, suction gauge reading +0.2 bar **gauge** (the reference is explicit
through `Pressure`), a 50 mm suction pipe and a pressure tap 1 m above the pump
reference, at the 9.8 m3/h duty.  The vapour pressure comes from `Water`.
"""),
        code(r"""
fluid = Water(Q_(20, "degC"))
q_rated = Q_(9.8, "m**3/h")
p_suction = Pressure(Q_(0.2, "bar"), "g")
suction_id = Q_(50, "mm")
z_suction = Q_(1.0, "m")

npsha = npsh_available(p_suction, fluid, q_rated, suction_id=suction_id, z_suction=z_suction)

# independent hand computation of the same equation
p_abs = p_suction.absolute()
pressure_head = ((p_abs - fluid.vapour_pressure) / (fluid.density * G)).to("m")
velocity = (q_rated / (math.pi * suction_id**2 / 4)).to("m/s")
velocity_head = (velocity**2 / (2 * G)).to("m")
manual = pressure_head + velocity_head + z_suction

print(f"p_abs = {p_abs.to('bar'):.4f~P}  p_v = {fluid.vapour_pressure.to('kPa'):.3f~P}")
print(f"pressure head {pressure_head:.3f~P} + velocity head {velocity_head:.3f~P} + z {z_suction:~P}")
print(f"NPSHa = {npsha:.3f~P}   (hand: {manual:.3f~P})")
"""),
        md(r"""
## 3 · NPSHr curve (points typed in feet)

Illustrative NPSHr points `0.5 + 0.02 Q + 0.004 Q^2` metres (1.08 m at the rated
flow), entered in **feet** and in gpm as an engineer would read them from a data sheet.
"""),
        code(r"""
q_m3h = [3.4, 6.6, 9.8, 11.8]
npshr_m = [round(0.5 + 0.02 * q + 0.004 * q * q, 3) for q in q_m3h]

q_points = tuple(Q_(q, "m**3/h").to("gallon/minute") for q in q_m3h)
r_points = tuple(Q_(r, "m").to("ft") for r in npshr_m)
npshr_curve = NPSHrCurve(q=q_points, npshr=r_points, degree=2)

npshr_rated = npshr_curve.at_rated(q_rated)
print("points:", [f"{q:.1f~P} -> {r:.2f~P}" for q, r in zip(q_points, r_points)])
print(f"NPSHr at the rated flow = {npshr_rated:.3f~P}")
print("extrapolated at 20 m3/h:", npshr_curve.extrapolated(Q_(20, "m**3/h")))
"""),
        md(r"""
## 4 · NPSH3 from a suction sweep

At a fixed flow the suction is throttled and the head is recorded.  NPSH3 is the NPSHa
at which the head has dropped by 3 % from the mean of the first two points
(linear interpolation between the bracketing points).
"""),
        code(r"""
sweep_npsha = [Q_(v, "m") for v in (8, 7, 6, 5, 4, 3)]
sweep_head = [Q_(v, "m") for v in (100, 100, 100, 90, 80, 70)]
npsh3 = npsh3_from_sweep(sweep_npsha, sweep_head)
print(f"NPSH3 = {npsh3:.3f~P}")

try:
    npsh3_from_sweep(sweep_npsha, [Q_(100, "m")] * 6)
    never_drops = False
except ValueError as exc:
    never_drops = True
    print("ValueError:", exc)
"""),
        md(r"""
## 5 · Ratio, margin and the verdict

Without a configured rule the status is `info`.  With the illustrative rule
`NPSHa / NPSHr >= 1.3` and `margin >= 0.6 m` it becomes `pass` or `fail`.  A second
scenario with a vacuum suction (-0.8 bar gauge) has a much lower NPSHa.
"""),
        code(r"""
low = npsh_available(
    Pressure(Q_(-0.8, "bar"), "g"), fluid, q_rated, suction_id=suction_id, z_suction=z_suction
)
rule = NPSHCriteria(min_ratio=1.3, min_margin=Q_(0.6, "m"), source="illustrative demo rule")
strict = NPSHCriteria(min_ratio=3.5, source="illustrative strict rule")

margin = npsh_margin(npsha, npshr_rated)
print(f"ratio = {margin['ratio']:.2f}   margin = {margin['margin']:.2f~P}")

results = {
    "no rule": check_npsh(npsha, npshr_rated),
    "demo rule": check_npsh(npsha, npshr_rated, rule),
    "low suction, demo rule": check_npsh(low, npshr_rated, rule),
    "low suction, strict rule": check_npsh(low, npshr_rated, strict),
}
for name, res in results.items():
    print(f"{name:<26} NPSHa {res.npsha:6.2f~P}  ratio {res.ratio:5.2f}  -> {res.status}")
"""),
        code(r"""
png = plot_npsh(npshr_curve, npsha=npsha, rated_q=q_rated)
display(Image(data=png.getvalue()))
"""),
        md("## 6 · Acceptance"),
        code(r"""
# NPSHa equals the independent computation (and has the right order of magnitude)
assert abs((npsha - manual).to("m").magnitude) < 1e-9
assert 13.0 < npsha.to("m").magnitude < 13.6
assert 2.9 < low.to("m").magnitude < 3.2

# the fitted NPSHr reproduces the rated point and is not extrapolated there
assert abs(npshr_rated.to("m").magnitude - 1.08) < 0.01
assert npshr_curve.extrapolated(q_rated) is False
assert npshr_curve.extrapolated(Q_(20, "m**3/h")) is True

# NPSH3 by interpolation (the sweep example of the docstring)
assert abs(npsh3.to("m").magnitude - 5.7) < 1e-9
assert never_drops

# margin arithmetic and verdicts
assert abs(margin["ratio"] - npsha.to("m").magnitude / npshr_rated.to("m").magnitude) < 1e-9
assert results["no rule"].status == "info"
assert results["demo rule"].status == "pass"
assert results["low suction, demo rule"].status == "pass"
assert results["low suction, strict rule"].status == "fail"
assert NPSHCriteria().configured is False
print("UC-05 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-07 Trim
# --------------------------------------------------------------------------- #
def uc07():
    return [
        md(r"""
# UC-07 · Evaluate an impeller trim

**Use case:** [UC-07](../docs/product/use-cases.md) - *which impeller diameter makes
the pump meet its rated duty, and what does the trimmed curve look like?*

Method: pure **diameter affinity** (speed unchanged), the same family of laws as the
speed affinity of UC-06:

$$ \frac{Q_2}{Q_1} = \frac{D_2}{D_1},\quad \frac{H_2}{H_1} = \Big(\frac{D_2}{D_1}\Big)^2,\quad
\frac{P_2}{P_1} = \Big(\frac{D_2}{D_1}\Big)^3,\quad \eta_2 = \eta_1 $$

`PerformanceCurve.to_diameter` applies it (and warns beyond 5 % trim);
`pump.trim.diameter_for_duty` intersects the affinity parabola through the duty with
the fitted head curve and returns the diameter.

The curve is **P-9001A** (128 mm impeller, 10 212 rpm, datasheet range 125-131 mm)
corrected to its rated fluid; the duty is the rated 9.80 m3/h at 333.8 m.

**Acceptance:** the needed diameter is about 127.1 mm (-0.7 %); the trimmed curve
passes through the duty; efficiency is unchanged and power scales as D^3.
"""),
        md("## 1 · Setup and the P-9001A curve"),
        code(COMMON_SETUP + r"""
from pump.trim import affinity_intersection, diameter_for_duty

# P-9001A at 10212 rpm, rated fluid (examples/catalogue/P-9001A.pumpcurve.json, rounded)
#       Q [m3/h]  Head [m]  P [kW]  eta [%]
P9001A = [
    (3.4225, 367.746, 18.707, 18.309),
    (6.6198, 365.823, 21.219, 31.058),
    (7.8357, 359.727, 22.492, 34.103),
    (9.7946, 340.692, 24.540, 37.005),
    (10.7853, 321.698, 25.805, 36.589),
    (11.7535, 302.235, 26.923, 35.906),
]
fluid = Fluid("Wash water (rated)", density=Q_(999.0, "kg/m**3"))
speed = Q_(10212, "rpm")
d_ref = Q_(128, "mm")

points = [
    TestPoint(
        fluid=fluid,
        capacity=Q_(q, "m**3/h"),
        speed_of_rotation=speed,
        _head=Q_(h, "m"),
        _efficiency=Q_(e, "percent"),
        breaking_power=Q_(p, "kW"),
    )
    for q, h, p, e in P9001A
]
curve = PerformanceCurve(fluid, points, polynomial_degree=3)

duty_q, duty_h = Q_(9.80, "m**3/h"), Q_(333.8, "m")
print("untrimmed head at the duty flow:", curve.predict_head(duty_q).to("m"))
"""),
        md(r"""
## 2 · The diameter that meets the duty

The affinity parabola $H = (h/q^2) Q^2$ through the duty meets the head curve at
$Q_1$; then $D = D_{ref}\, q / Q_1$.
"""),
        code(r"""
q1 = affinity_intersection(curve, duty_q, duty_h)
d_new = diameter_for_duty(curve, duty_q, duty_h, d_ref)
change = (d_new / d_ref).to("dimensionless").magnitude - 1.0
print(f"Q1 = {q1:.3f~P}   D = {d_new:.2f~P}   ({change:+.2%} vs {d_ref:~P})")
print("inside the datasheet range 125-131 mm:", 125 <= d_new.to("mm").magnitude <= 131)
"""),
        md(r"""
## 3 · The trimmed curve

`to_diameter` returns a **new** curve; the original is untouched.
"""),
        code(r"""
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    trimmed = curve.to_diameter(d_new, d_ref)
print("warnings for a", f"{change:+.1%}", "trim:", [str(w.message) for w in caught])

ratio = (d_new / d_ref).to("dimensionless").magnitude
print(f"{'Q m3/h':>8} {'H m':>8} {'P kW':>7} {'eta %':>6}")
for p in trimmed.points:
    print(
        f"{p.capacity.magnitude:8.3f} {p.head.magnitude:8.2f} "
        f"{p.breaking_power.magnitude:7.2f} {p.efficiency.magnitude:6.2f}"
    )

fig, ax = plt.subplots(figsize=(7, 4.5))
for c, label in ((curve, "128 mm"), (trimmed, f"{d_new.magnitude:.1f} mm")):
    caps = np.asarray(c.fitter.capacities, dtype=float)
    xs = np.linspace(caps.min(), caps.max(), 100)
    ax.plot(xs, np.polyval(c.fitter.head_coeffs, xs), label=label)
ax.plot(duty_q.magnitude, duty_h.magnitude, "k*", ms=14, label="rated duty")
ax.set_xlabel("Capacity (m3/h)")
ax.set_ylabel("Head (m)")
ax.grid(alpha=0.3)
ax.legend(title="Impeller")
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 4 · Limits of the method

A trim beyond `max_trim` (5 % by default) warns that the approximation loses accuracy;
a duty that the curve cannot reach by trimming raises `ValueError`.
"""),
        code(r"""
with warnings.catch_warnings(record=True) as caught_big:
    warnings.simplefilter("always")
    big = curve.to_diameter(Q_(110, "mm"), d_ref)
big_warned = any(issubclass(w.category, UserWarning) for w in caught_big)

with warnings.catch_warnings(record=True) as caught_ok:
    warnings.simplefilter("always")
    curve.to_diameter(Q_(110, "mm"), d_ref, max_trim=0.2)
big_ok = not caught_ok

try:
    diameter_for_duty(curve, duty_q, Q_(50, "m"), d_ref)
    unreachable = False
except ValueError as exc:
    unreachable = True
    print("ValueError:", str(exc)[:110], "...")
"""),
        md("## 5 · Acceptance"),
        code(r"""
# diameter (regression value of the project: 127.1 mm, -0.7 %)
assert 126.9 < d_new.to("mm").magnitude < 127.3
assert -0.012 < change < -0.003
assert abs(d_new.to("mm").magnitude - 128 * 9.80 / q1.magnitude) < 1e-9

# no warning for a small trim; the original curve is not mutated
assert not caught
assert curve.points[0].capacity.magnitude == P9001A[0][0]

# the trimmed curve passes through the duty
assert abs(trimmed.predict_head(duty_q).to("m").magnitude - 333.8) < 1e-3

# affinity laws, point by point; eta unchanged
for old, new in zip(curve.points, trimmed.points):
    assert abs(new.capacity.magnitude - old.capacity.magnitude * ratio) < 1e-9
    assert abs(new.head.magnitude - old.head.magnitude * ratio**2) < 1e-9
    assert abs(new.breaking_power.magnitude - old.breaking_power.magnitude * ratio**3) < 1e-9
    assert abs(new.efficiency.magnitude - old.efficiency.magnitude) < 1e-12

# limits
assert big_warned and big_ok and unreachable
print("UC-07 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-08 Compare
# --------------------------------------------------------------------------- #
def uc08():
    return [
        md(r"""
# UC-08 · Compare twin pumps (A vs B)

**Use case:** [UC-08](../docs/product/use-cases.md) - *two pumps built for the same
service are tested; how do they differ?*

`pump.compare.compare_curves` evaluates H, P and eta of several fitted curves at the
chosen capacities and reports the relative delta $(x - x_{ref})/x_{ref}$ against the
**first** curve (the reference).  `plot_comparison` overlays the curves.

Pump A is the P-1001A water test.  Pump B is a synthetic twin whose head is 2 % lower
and whose power is 3 % higher; its efficiency is set consistently with both.

**Acceptance:** the reported deltas equal the injected differences (-2 %, +3 % and
$0.98/1.03 - 1$).
"""),
        md("## 1 · Setup and the two curves"),
        code(COMMON_SETUP + P1001A_DATA + r"""
from pump.compare import compare_curves, plot_comparison

speed = Q_(1480, "rpm")
curve_a = build_curve(P1001A, water, speed)
curve_b = build_curve(P1001A, water, speed, head_k=0.98, power_k=1.03, eff_k=0.98 / 1.03)
curves = {"P-1001A": curve_a, "P-1001B": curve_b}
"""),
        md(r"""
## 2 · The comparison table

Capacities are Pint quantities in any unit.
"""),
        code(r"""
at = [Q_(240, "m**3/h"), Q_(320, "m**3/h"), Q_(1409, "gallon/minute")]
table = compare_curves(curves, at)
print("reference:", table.tags[0])
print(table.as_text())
"""),
        md("## 3 · Overlay plot"),
        code(r"""
png = plot_comparison(curves, rated_q=Q_(320, "m**3/h"))
display(Image(data=png.getvalue()))
"""),
        md(r"""
## 4 · A single curve cannot be compared
"""),
        code(r"""
try:
    compare_curves({"only": curve_a}, at)
    needs_two = False
except ValueError as exc:
    needs_two = True
    print("ValueError:", exc)
"""),
        md("## 5 · Acceptance"),
        code(r"""
assert table.tags == ("P-1001A", "P-1001B")
assert len(table.rows) == 3
for row in table.rows:
    # the reference carries no delta; B differs by the injected factors
    assert "P-1001A" not in row.deltas
    d = row.deltas["P-1001B"]
    assert abs(d["head"] - (-0.02)) < 1e-6
    assert abs(d["power"] - 0.03) < 1e-6
    assert abs(d["efficiency"] - (0.98 / 1.03 - 1.0)) < 1e-6

# the 1409 gpm row is the 320 m3/h row in other units
assert abs(table.rows[2].q.to("m**3/h").magnitude - 320.0) < 0.2
assert needs_two
print("UC-08 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-09 Reports
# --------------------------------------------------------------------------- #
def uc09():
    return [
        md(r"""
# UC-09 · Generate the FAT report (docx, tex, pdf; en / pt)

**Use case:** [UC-09](../docs/product/use-cases.md) - *test complete, deliverable due.*

The library renders one `report_data` dictionary to three formats:

- `.docx` with `pump.utilities.report.ReportGenerator`;
- `.tex` (and its figures folder) with `LatexReportGenerator.generate_tex`;
- `.pdf` with `LatexReportGenerator.generate_pdf`, **only if a TeX engine is found**
  (`find_latex_engine()`; otherwise the PDF step is skipped and reported).

`language="en"` or `"pt"` selects the gettext catalogue and the template.  The
dictionary is built here by hand from library objects (design point, checker summary,
fitted curve, mechanical run, NPSH, comparison); the workbench does the same through
`pumpflow.binding.assemble_report_data`.  Everything is written to a temporary
directory.

**Acceptance:** the files exist and are non-empty, the docx re-opens and carries the
verdict in the right language, the LaTeX source carries the figures, and the PDF (when
a TeX engine exists) is a valid PDF.
"""),
        md("## 1 · Setup and the test data"),
        code(COMMON_SETUP + P1001A_DATA + r"""
import math
import tempfile
from pathlib import Path

from docx import Document

from pump import (
    AcceptanceCriteria,
    Channel,
    DesignPoint,
    MechanicalRunChecker,
    MechanicalRunLog,
    NPSHrCurve,
    PerformanceChecker,
    Pressure,
    RunReading,
    check_npsh,
    npsh_available,
    plot_mechanical_run,
    plot_npsh,
)
from pump.compare import compare_curves, plot_comparison
from pump.utilities.report import ReportGenerator
from pump.utilities.report_latex import LatexReportGenerator, find_latex_engine

speed = Q_(1480, "rpm")
"""),
        md(r"""
## 2 · The `report_data` builder

A function, because the chart streams (`BytesIO`) are consumed once by each writer.
"""),
        code(r"""
def make_mechanical():
    channels = (
        Channel("Filtered vibration", "vibration_filtered"),
        Channel("Unfiltered vibration", "vibration_unfiltered"),
        Channel("Bearing temperature", "bearing_temperature"),
    )
    readings = []
    for i in range(17):  # every 15 min for 4 h
        minutes = 15 * i
        readings.append(
            RunReading(
                f"{10 + minutes // 60:02d}:{minutes % 60:02d}",
                {
                    "Filtered vibration": Q_(0.05, "in/s"),
                    "Unfiltered vibration": Q_(0.09, "in/s"),
                    "Bearing temperature": Q_(150 + 0.5 * i, "degF"),
                },
            )
        )
    log = MechanicalRunLog(channels, readings)
    criteria = AcceptanceCriteria.load("api610:12").mechanical_run
    return {
        "result": MechanicalRunChecker(log, criteria).check(),
        "plot": plot_mechanical_run(log, criteria),
    }


def make_npsh(design):
    fluid = Water(Q_(20, "degC"))
    npsha = npsh_available(
        Pressure(Q_(0.2, "bar"), "g"), fluid, design.capacity,
        suction_id=Q_(150, "mm"), z_suction=Q_(1.0, "m"),
    )
    q = tuple(Q_(v, "m**3/h") for v in (160, 240, 320, 400))
    r = tuple(Q_(v, "m") for v in (2.0, 2.4, 3.0, 3.9))
    curve = NPSHrCurve(q, r, degree=2)
    result = check_npsh(npsha, curve.at_rated(design.capacity))
    return {"result": result, "plot": plot_npsh(curve, npsha, design.capacity),
            "table": list(zip(curve.q, curve.npshr))}


def make_report_data():
    curve = build_curve(P1001A, water, speed)
    design = DesignPoint(
        fluid=water,
        capacity=Q_(320, "m**3/h"),
        differential_head=Q_(110, "m"),
        breaking_power=Q_(115, "kW"),
    )
    criteria = AcceptanceCriteria.load("api610:12")
    checker = PerformanceChecker(design, curve, criteria=criteria)

    pred_h = curve.predict_head(design.capacity)
    pred_p = curve.predict_breaking_power(design.capacity)
    passed = bool(
        checker.minimum_head <= pred_h <= checker.maximum_head
        and pred_p <= checker.maximum_breaking_power
    )

    curve_b = build_curve(P1001A, water, speed, head_k=0.98, power_k=1.03, eff_k=0.98 / 1.03)
    curves = {"P-1001A": curve, "P-1001B": curve_b}
    comparison = {
        "table": compare_curves(curves, [design.capacity]),
        "plot": plot_comparison(curves, rated_q=design.capacity),
        "at": [design.capacity],
    }
    entry = {
        "test_summary": checker.report_summary,
        "test_data": curve.test_data,
        "verdict": passed,
        "Performance Curve": curve.plot_performance_curve(
            capacity=design.capacity, return_io=True
        ),
        "Mechanical Run": make_mechanical(),
        "NPSH": make_npsh(design),
    }
    return {
        "equipment_description": {
            "TAG": "P-1001A",
            "Manufacturer": "Demo Pumps",
            "Service": "Cooling water",
        },
        "design_point": design,
        "test_data": {"P-1001A": entry},
        "acceptance": {
            "label": criteria.label,
            "verified": bool(criteria.verified),
            "unverified": list(criteria.unverified),
        },
        "comparison": comparison,
    }


probe = make_report_data()
print("sections:", sorted(probe["test_data"]["P-1001A"]), "+ comparison")
print("verdict :", probe["test_data"]["P-1001A"]["verdict"])
"""),
        md(r"""
## 3 · Write every format

Each language gets a `.docx` and a `.tex`; the PDF is compiled only when a TeX engine
is available, and a compilation problem in the local TeX installation is reported
rather than raised (the `.tex` assertions still cover the content).
"""),
        code(r"""
engine = find_latex_engine()
print("TeX engine:", engine)

docx_text, tex_text, sizes = {}, {}, {}
pdf_status = "skipped (no TeX engine found)" if engine is None else "not run"
pdf_bytes = None
n_figures = {}

with tempfile.TemporaryDirectory() as tmp_name:
    tmp = Path(tmp_name)
    for lang in ("en", "pt"):
        docx_path = Path(
            ReportGenerator(language=lang).generate_report(
                make_report_data(), output_file=str(tmp / f"report_{lang}.docx")
            )
        )
        tex_path = Path(
            LatexReportGenerator(language=lang).generate_tex(
                make_report_data(), str(tmp / f"report_{lang}.tex")
            )
        )
        doc = Document(str(docx_path))
        docx_text[lang] = "\n".join(p.text for p in doc.paragraphs)
        tex_text[lang] = tex_path.read_text(encoding="utf-8")
        figs = tmp / f"report_{lang}_figs"
        n_figures[lang] = len(list(figs.glob("*.png"))) if figs.is_dir() else 0
        sizes[lang] = (docx_path.stat().st_size, tex_path.stat().st_size)

    if engine is not None:
        try:
            pdf_path = LatexReportGenerator(language="en").generate_pdf(
                make_report_data(), str(tmp / "report_en.pdf")
            )
            pdf_bytes = Path(pdf_path).read_bytes()
            pdf_status = f"compiled ({len(pdf_bytes)} bytes)"
        except RuntimeError as exc:
            pdf_status = "TeX engine found but the build failed: " + str(exc)[:150]

print("sizes (docx, tex):", sizes)
print("figures per language:", n_figures)
print("PDF:", pdf_status)
"""),
        md("## 4 · Acceptance"),
        code(r"""
for lang in ("en", "pt"):
    assert sizes[lang][0] > 10_000, "docx is empty"
    assert sizes[lang][1] > 2_000, "tex is empty"
    assert n_figures[lang] >= 3, "performance, NPSH/mechanical and comparison figures"

# the docx carries the pump tag and the localised verdict (API 610 12th ed.
# Table 16 is checked against the text, so the verdict is not provisional)
assert "P-1001A" in docx_text["en"] and "P-1001A" in docx_text["pt"]
assert "Overall verdict" in docx_text["en"] and "APPROVED" in docx_text["en"]
assert "APPROVED (unverified criteria)" not in docx_text["en"]
assert "Resultado geral" in docx_text["pt"] and "APROVADO" in docx_text["pt"]
assert "Dados do Teste" in docx_text["pt"]

# the LaTeX source is localised too, and lists the comparison section
assert r"\section{Introduction}" in tex_text["en"]
assert "Introdu" in tex_text["pt"] and "brazilian" in tex_text["pt"]
assert "Comparison" in tex_text["en"]
assert r"\includegraphics" in tex_text["en"]

# the PDF exists only when a TeX engine is installed; if built it is a real PDF
if pdf_bytes is not None:
    assert pdf_bytes.startswith(b"%PDF")
print("UC-09 acceptance OK  | PDF:", pdf_status)
"""),
    ]


# --------------------------------------------------------------------------- #
# UC-11 Mechanical run
# --------------------------------------------------------------------------- #
def uc11():
    return [
        md(r"""
# UC-11 · Mechanical running test acceptance

**Use case:** [UC-11](../docs/product/use-cases.md) - *a 4 h mechanical run is logged
every 15 min; accept or reject it.*

`pump.mechanical_run` models a time-stamped log of channels, each with a **role**
(`vibration_filtered`, `bearing_temperature`, ...), a unit chosen by the engineer, and
a checker that compares each channel with a criterion of its role:

- an upper limit on the channel maximum;
- an optional *stabilisation* rule: over the last window, max - min must stay below a
  change (temperature differences use `delta_degF`);
- the minimum run duration.

A check without a configured criterion reports `info`, never pass or fail, and the
verdict then reads *PASSED (not fully assessed)*.

> The shipped limits (4 h, 2.0 / 3.0 mm/s RMS) are **unverified** seeds.  The second
> criteria set in this notebook is an *illustrative demo* set, not a standard.

**Acceptance:** the demo run passes against the shipped criteria (not fully assessed)
and against the demo criteria; a vibration spike, a short run and an unstable oil
temperature each fail.
"""),
        md("## 1 · Setup"),
        code(r"""
import math

import matplotlib.pyplot as plt
from IPython.display import Image, display

from pump import (
    AcceptanceCriteria,
    Channel,
    MechanicalRunChecker,
    MechanicalRunCriteria,
    MechanicalRunLog,
    Q_,
    RunReading,
    plot_mechanical_run,
)
"""),
        md(r"""
## 2 · A 4 h log in the engineer's units

Vibration in in/s, temperatures in degF, one reading every 15 min from 10:00 to 14:00
(17 readings).  Options inject a vibration spike, shorten the run or keep the oil
temperature rising.
"""),
        code(r"""
CHANNELS = (
    Channel("Filtered vibration", "vibration_filtered"),
    Channel("Unfiltered vibration", "vibration_unfiltered"),
    Channel("Bearing temperature", "bearing_temperature"),
    Channel("Oil temperature", "oil_temperature"),
)


def make_log(n=17, spike=None, oil_ramp=False):
    readings = []
    for i in range(n):
        minutes = 15 * i
        oil = 100.0 + 1.5 * i if oil_ramp else 118.0 + 10.0 * (1.0 - math.exp(-i / 2.5))
        unfiltered = 0.16 if spike == i else 0.09
        readings.append(
            RunReading(
                f"{10 + minutes // 60:02d}:{minutes % 60:02d}",
                {
                    "Filtered vibration": Q_(0.05, "in/s"),
                    "Unfiltered vibration": Q_(unfiltered, "in/s"),
                    "Bearing temperature": Q_(150.0 + 0.5 * i, "degF"),
                    "Oil temperature": Q_(oil, "degF"),
                },
            )
        )
    return MechanicalRunLog(CHANNELS, readings)


log = make_log()
print("readings:", len(log.readings), "| duration:", log.duration.to("h"))
"""),
        md(r"""
## 3 · Against the shipped criteria (API 610 12th seeds)

Vibration limits and the 4 h duration are configured; temperatures are not, so those
channels are `info` and the run is *not fully assessed*.
"""),
        code(r"""
shipped = AcceptanceCriteria.load("api610:12").mechanical_run
res_shipped = MechanicalRunChecker(log, shipped).check()
print("verdict:", res_shipped.verdict, "| verified criteria:", res_shipped.verified)
for c in res_shipped.channels:
    print(f"  {c.name:<22} max {c.max.magnitude:7.2f} {c.unit:<6} limit {c.limit} -> {c.status}")
"""),
        md(r"""
## 4 · Against an illustrative full criteria set

Adds a bearing-temperature maximum of 95 degC and an oil-temperature stabilisation rule
(change <= 2 delta_degF over the last 60 min).
"""),
        code(r"""
demo = MechanicalRunCriteria(
    min_duration=Q_(4, "h"),
    role_max={
        "vibration_filtered": Q_(2.0, "mm/s"),
        "vibration_unfiltered": Q_(3.0, "mm/s"),
        "bearing_temperature": Q_(95, "degC"),
    },
    stabilisation={"oil_temperature": (Q_(2, "delta_degF"), Q_(60, "min"))},
    source="illustrative demo limits",
    verified=False,
)
res_ok = MechanicalRunChecker(log, demo).check()
print("verdict:", res_ok.verdict)
for c in res_ok.channels:
    print(f"  {c.name:<22} {c.status:<5} stabilisation: {c.stabilisation and c.stabilisation['ok']}")

png = plot_mechanical_run(log, demo)
display(Image(data=png.getvalue()))
"""),
        md(r"""
## 5 · Three ways to fail

A single unfiltered-vibration spike of 0.16 in/s (4.06 mm/s), a run that stops after 2 h,
and an oil temperature that is still rising at the end of the run.
"""),
        code(r"""
res_spike = MechanicalRunChecker(make_log(spike=8), demo).check()
res_short = MechanicalRunChecker(make_log(n=9), demo).check()
res_ramp = MechanicalRunChecker(make_log(oil_ramp=True), demo).check()

for name, res in (("spike", res_spike), ("short run", res_short), ("oil still rising", res_ramp)):
    failing = [c.name for c in res.channels if c.status == "fail"]
    print(f"{name:<18} {res.verdict:<8} duration {res.duration_status:<5} failing channels: {failing}")

print("4.06 mm/s check:", Q_(0.16, "in/s").to("mm/s"))
"""),
        md("## 6 · Acceptance"),
        code(r"""
# the demo log is 4 h long
assert abs(log.duration.to("h").magnitude - 4.0) < 1e-9
assert len(log.readings) == 17

# shipped criteria: nothing fails, but the temperatures are not assessed
assert res_shipped.passed and res_shipped.verdict == "PASSED (not fully assessed)"
assert res_shipped.fully_assessed is False
assert res_shipped.verified is False

# demo criteria: fully assessed and passed (still unverified criteria)
assert res_ok.passed and res_ok.fully_assessed and res_ok.verdict == "PASSED"
by_name = {c.name: c for c in res_ok.channels}
assert by_name["Oil temperature"].stabilisation["ok"] is True
assert by_name["Oil temperature"].status == "pass"

# failures
assert res_spike.verdict == "FAILED"
assert {c.name: c.status for c in res_spike.channels}["Unfiltered vibration"] == "fail"
assert res_short.verdict == "FAILED" and res_short.duration_status == "fail"
assert res_ramp.verdict == "FAILED"
assert {c.name: c.status for c in res_ramp.channels}["Oil temperature"] == "fail"
assert abs(Q_(0.16, "in/s").to("mm/s").magnitude - 4.064) < 1e-3
print("UC-11 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# Viscosity HI 9.6.7
# --------------------------------------------------------------------------- #
def viscosity():
    return [
        md(r"""
# Viscosity correction (HI 9.6.7 / ISO TR 17766)

**Use case:** performance on a viscous liquid predicted from a water test.  This is
the worked example of the *Correction* step of the workbench.

At the water best-efficiency point (BEP-W), with $\nu$ in cSt, $H$ in ft per stage,
$Q$ in gpm and $N$ in rpm:

$$ B = \frac{26.6\,\nu^{0.5}\,H^{0.0625}}{Q^{0.375}\,N^{0.25}},\quad
C_Q = 2.71^{-0.165\,\log_{10}(B)^{3.15}},\quad
C_H = 1-(1-C_Q)\Big(\frac{Q}{Q_{BEP}}\Big)^{0.75},\quad
C_\eta = B^{-0.0547\,B^{0.69}} $$

Valid for $1 < B < 40$; for $B \le 1$ there is no correction.  `pump.viscosity` provides
`b_parameter` and `correction_factors`; `PerformanceCurve.bep()` and
`PerformanceCurve.to_viscous` apply them to a whole curve (every point becomes
$Q\,C_Q$, $H\,C_H(Q/Q_{BEP})$, $\eta\,C_\eta$ and the power is recomputed with the
viscous density).

> The equations are ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by a **secondary source**.
> They were cross-checked independently but **not** against the standard text.

**Acceptance:** B and the factors match a hand computation; the viscous BEP moves by
$C_Q$ and $C_\eta$; B <= 1 is bit-identical to a density-only change; B >= 40 warns.
"""),
        md("## 1 · Setup and the water test"),
        code(COMMON_SETUP + P1001A_DATA + r"""
from pump import b_parameter, correction_factors

speed = Q_(1480, "rpm")
water_curve = build_curve(P1001A, water, speed)
q_bep, h_bep, eta_bep = water_curve.bep()
print(f"BEP (water): Q = {q_bep:.1f~P}  H = {h_bep:.1f~P}  eta = {eta_bep:.1f~P}")
"""),
        md(r"""
## 2 · B and the factors for a 100 cSt oil

The liquid carries its density and kinematic viscosity (any unit; here 100 cSt).
`b_parameter` takes Pint quantities and converts to the US units of the equation.
"""),
        code(r"""
oil = Fluid("Lube oil", density=Q_(880.0, "kg/m**3"), kinematic_viscosity=Q_(100.0, "cSt"))
nu = oil.kinematic_viscosity

b = b_parameter(nu, q_bep, h_bep, speed)
c_q, c_h, c_eta = correction_factors(b)   # at the BEP: C_H = C_Q
print(f"B = {b:.3f}  C_Q = {c_q:.4f}  C_H(BEP) = {c_h:.4f}  C_eta = {c_eta:.4f}")

# the same B by hand, in the US units of the equation
nu_cst = nu.to("cSt").magnitude
q_gpm = q_bep.to("gallon/minute").magnitude
h_ft = h_bep.to("ft").magnitude
n_rpm = speed.to("rpm").magnitude
b_hand = 26.6 * nu_cst**0.5 * h_ft**0.0625 / (q_gpm**0.375 * n_rpm**0.25)
print(f"B by hand = {b_hand:.3f}")
"""),
        md(r"""
## 3 · The corrected curve

`to_viscous` returns a **new** curve and stores the BEP factors in `viscosity_correction`.
"""),
        code(r"""
viscous = water_curve.to_viscous(oil)
vc = viscous.viscosity_correction
print({k: round(v, 4) for k, v in vc.items()})

q_v, h_v, eta_v = viscous.bep()
print(f"BEP (viscous): Q = {q_v:.1f~P}  H = {h_v:.1f~P}  eta = {eta_v:.1f~P}")

fig, axes = plt.subplots(3, 1, sharex=True, figsize=(7, 8))
for curve_, label in ((water_curve, "water"), (viscous, "oil 100 cSt")):
    caps = np.asarray(curve_.fitter.capacities, dtype=float)
    xs = np.linspace(caps.min(), caps.max(), 150)
    axes[0].plot(xs, np.polyval(curve_.fitter.head_coeffs, xs), label=label)
    axes[1].plot(xs, np.polyval(curve_.fitter.power_coeffs, xs))
    axes[2].plot(xs, np.polyval(curve_.fitter.efficiency_coeffs, xs))
axes[0].set_ylabel("Head (m)")
axes[1].set_ylabel("Power (kW)")
axes[2].set_ylabel("Efficiency (%)")
axes[2].set_xlabel("Capacity (m3/h)")
axes[0].legend()
for ax in axes:
    ax.grid(alpha=0.3)
fig.tight_layout()
plt.show()
"""),
        md(r"""
## 4 · Edge cases

Hot water (B <= 1) is *not* corrected: `to_viscous` equals a density-only `to_fluid`.
Two stages halve the head per stage in B.  B >= 40 is outside the method and warns.
"""),
        code(r"""
hot = Water(Q_(60, "degC"))
low_b = water_curve.to_viscous(hot)
density_only = water_curve.to_fluid(hot)

two_stage = water_curve.to_viscous(oil, stages=2)

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    correction_factors(45.0)
warned = any(issubclass(w.category, UserWarning) for w in caught)

print("B(hot water, 60 degC) =", round(low_b.viscosity_correction["B"], 3))
print("B with 2 stages       =", round(two_stage.viscosity_correction["B"], 3))
print("B = 45 warns          =", warned)
"""),
        md("## 5 · Acceptance"),
        code(r"""
# B and the factors
assert 1.0 < b < 40.0
assert abs(b - b_hand) < 1e-12
assert abs(vc["B"] - b) < 1e-12
assert (vc["C_Q"], vc["C_H"], vc["C_eta"]) == (c_q, c_h, c_eta)
assert 0.0 < c_eta < c_q <= 1.0

# the viscous BEP moves by C_Q (flow, head) and C_eta (efficiency)
assert abs(q_v.magnitude / q_bep.magnitude - c_q) < 0.01
assert abs(h_v.magnitude / h_bep.magnitude - c_q) < 0.02
assert abs(eta_v.magnitude / eta_bep.magnitude - c_eta) < 0.02

# shut-off head is not corrected: C_H(Q=0) = 1, continuity at B = 1
assert correction_factors(5.0, 0.0)[1] == 1.0
assert max(abs(x - 1.0) for x in correction_factors(1.0 + 1e-9)) < 1e-6
assert correction_factors(0.5) == (1.0, 1.0, 1.0)

# B <= 1 is bit-identical to a density-only change
assert low_b.viscosity_correction["B"] <= 1.0
q_test = Q_(320, "m**3/h")
assert low_b.predict_head(q_test).magnitude == density_only.predict_head(q_test).magnitude
assert low_b.predict_breaking_power(q_test).magnitude == density_only.predict_breaking_power(q_test).magnitude

# stages lower B; the original curve is untouched; B >= 40 warns
assert two_stage.viscosity_correction["B"] < vc["B"]
assert water_curve.viscosity_correction is None
assert warned
print("Viscosity HI 9.6.7 acceptance OK")
"""),
    ]


# --------------------------------------------------------------------------- #
# TR-01 - Witness training: API 610 performance test
# --------------------------------------------------------------------------- #
def tr01():
    return [
        md(r"""
# TR-01 · Witnessing an API 610 performance test (exercises)

Companion of the training guide
[TR-01](../docs/training/TR-01-witness-performance-test.md).  Every exercise of the guide
is worked here with the `pump` library, and the last cell **asserts** the answers.

The tolerance tables come from `pump/standards/api610.toml` and
`pump/standards/clients/n553.toml`; they were checked against API 610 8th, 11th, 12th
editions and Petrobras N-553 rev E (clause references in each table's `source`).
"""),
        code(r"""
from pump import Q_
from IPython.display import Image, display

from pump.acceptance import AcceptanceCriteria, deviation, head_rises_to_shutoff
from pump.npsh import check_npsh

api8 = AcceptanceCriteria.load("api610:8")
api11 = AcceptanceCriteria.load("api610:11")
p9001 = AcceptanceCriteria.load("api610:8", client="n553")
print(p9001.label, "+", p9001.client_label)
print("verified performance tolerances:", p9001.verified,
      "| open parts:", p9001.unverified)
"""),
        md(r"""
## Exercise 1 · Which band? (rated head 120 m)

The band is chosen by the **rated** head, for the shut-off check too.  Note the shut-off
edge: 150 m in the 8th edition, 75 m in the 11th.
"""),
        code(r"""
h = Q_(120, "m")
ex1 = {
    "8th head": api8.head_tolerance(h), "8th shut-off": api8.shutoff_tolerance(h),
    "11th head": api11.head_tolerance(h), "11th shut-off": api11.shutoff_tolerance(h),
}
for k, (minus, plus) in ex1.items():
    print(f"{k:14s} -{minus:.0%} / +{plus:.0%}")
"""),
        md(r"""
## Exercise 2 · P-9001A head (rated 333.8 m, predicted 339.5 m)
"""),
        code(r"""
rated_h, pred_h = Q_(333.8, "m"), Q_(339.5, "m")
dh = deviation(rated_h, pred_h)
minus, plus = p9001.head_tolerance(rated_h)
head_ok = -minus <= dh <= plus
print(f"dH = {dh:+.2%}  band -{minus:.0%}/+{plus:.0%}  -> {'PASS' if head_ok else 'FAIL'}"
      f"  (room left {plus - dh:.2%})")
print("under the 11th edition the band is", api11.head_tolerance(rated_h))
"""),
        md(r"""
## Exercise 3 · Power (rated 26.9 kW, predicted 24.6 kW)

+4 % from all causes, after the corrections; a lower power is not a defect.
"""),
        code(r"""
dp = deviation(Q_(26.9, "kW"), Q_(24.6, "kW"))
power_ok = dp <= p9001.power_tol_plus
print(f"dP = {dp:+.1%}  limit +{p9001.power_tol_plus:.0%}  -> {'PASS' if power_ok else 'FAIL'}")
"""),
        md(r"""
## Exercise 4 · Efficiency 3.7 % low, 37 kW driver

API 610 does not rate efficiency; N-553 rev E asks for -0 % only for drivers of 1 MW or
more.  The criteria carry **no** efficiency tolerance, so efficiency is information only.
"""),
        code(r"""
de = deviation(Q_(32.7, "percent"), Q_(31.5, "percent"))
print(f"d_eta = {de:+.1%}; efficiency tolerance in the criteria: {p9001.efficiency_tol_minus}")
"""),
        md(r"""
## Exercise 5 · NPSH (NPSHa 2.4 m, NPSH3 1.6 m, quoted 1.5 m)

Two rules: the client margin (N-553 rev E: >= 0.8 m and ratio >= 1.15) and API 610's
rated NPSH +0 % (tested NPSH3 <= quoted).
"""),
        code(r"""
res = check_npsh(Q_(2.4, "m"), Q_(1.6, "m"), p9001.npsh, npshr_quoted=Q_(1.5, "m"))
print(f"margin {res.margin:.2f~P}, ratio {res.ratio:.2f}, quoted ok: {res.quoted_ok}"
      f" -> NPSH verdict {res.status.upper()}")
needs_all_points = bool(res.margin < Q_(1.0, "m") or res.ratio < 1.20)
print("N-553 rev E 9.22: NPSHr at every test point required:", needs_all_points)
"""),
        md(r"""
## Exercise 6 · Vibration 0.16 in/s

The limit is 3.0 mm/s **RMS** (8th Table 2-5).  True peak may not be used for acceptance.
"""),
        code(r"""
v = Q_(0.16, "inch/s").to("mm/s")
limit = p9001.mechanical_run.role_max["vibration_unfiltered"]
vib_fails_if_rms = bool(v > limit)
print(f"0.16 in/s = {v:.2f~P}; limit {limit:~P} RMS -> "
      f"{'FAIL' if vib_fails_if_rms else 'PASS'} if the reading is RMS; "
      "if true peak: not usable, ask for RMS")
"""),
        md(r"""
## Exercise 7 · Test speed (rated 10 212 rpm, tested 10 301 rpm)
"""),
        code(r"""
dn = deviation(Q_(10212, "rpm"), Q_(10301, "rpm"))
speed_ok = abs(dn) <= 0.03
print(f"dN = {dn:+.2%} -> {'within' if speed_ok else 'outside'} 3 %")
"""),
        md(r"""
## Exercise 8 · Rising curve specified, shut-off 3 % low, curve droops

The negative shut-off tolerance is allowed only if the test curve still rises to
shut-off (`head_rises_to_shutoff`).  Two illustrative fitted curves through the same
rated point (9.8 m3/h, 333.8 m); the rated shut-off head is taken as 345 m.
"""),
        code(r"""
import numpy as np
import matplotlib.pyplot as plt

def poly(c):
    return lambda q: Q_(float(np.polyval(c, q.to("m**3/h").magnitude)), "m")

rated_q, rated_so = Q_(9.8, "m**3/h"), Q_(345.0, "m")
rising = poly([-0.24, 0.0, 356.85])          # head falls steadily with flow
drooping = poly([-0.04819, 0.3855, 334.65])  # head peaks near 4 m3/h, then falls
for name, f in (("rising", rising), ("drooping", drooping)):
    so = f(Q_(0, "m**3/h"))
    print(f"{name:9s} H(0) = {so:.1f~P} ({deviation(rated_so, so):+.1%} vs 345 m), "
          f"H(rated) = {f(rated_q):.1f~P}, rises to shut-off: "
          f"{head_rises_to_shutoff(f, rated_q)}")

qs = np.linspace(0, 12, 100)
for name, f in (("rising", rising), ("drooping", drooping)):
    plt.plot(qs, [f(Q_(q, "m**3/h")).magnitude for q in qs], label=name)
plt.axvline(9.8, ls=":", c="k")
plt.xlabel("Q (m3/h)"); plt.ylabel("Head (m)"); plt.legend(); plt.grid(alpha=0.3)
plt.show()
"""),
        md(r"""
## Exercise 9 · The test data summary's vibration columns

`vibration_by_region` fills the summary's rated / preferred / allowable columns from the
per-point RMS readings (rated = within 5 % of rated flow; preferred = 70-120 % of BEP;
allowable = every point except shut-off, limit +30 %).
"""),
        code(r"""
from pump.utilities.test_summary import vibration_by_region

readings = [(0.0, None), (5.0, 2.8), (9.9, 2.1), (11.0, 2.6), (12.5, 3.4)]
pts = [(Q_(q, "m**3/h"), {"vib_de": Q_(v, "mm/s")}) for q, v in readings if v]
limits = {"overall": p9001.mechanical_run.role_max["vibration_unfiltered"],
          "filtered": p9001.mechanical_run.role_max["vibration_filtered"]}
(de,) = vibration_by_region(pts, Q_(10, "m**3/h"), Q_(10, "m**3/h"), limits)
print("rated", de.rated, "| preferred", de.por, "| allowable", de.aor)
"""),
        md(r"""
## Exercise 10 · The high-speed vibration limit (11th/12th editions)

OH and BB pumps above 3600 r/min or 300 kW per stage:
v_u = 3.0 (n/3600)^0.30 (P/300)^0.21, kept between 3.0 and 4.5 mm/s; discrete 0.67 v_u;
P = BEP power at relative density 1.0 per stage (300 kW minimum).  The 8th edition has
no such allowance.
"""),
        code(r"""
from pump.vibration import HighSpeedRule, plot_high_speed_chart

n, p_bep = Q_(10212, "rpm"), Q_(25, "kW")
lim12 = AcceptanceCriteria.load("api610:12").vibration.limits("OH6", n, p_bep)
lim8 = AcceptanceCriteria.load("api610:8").vibration.limits("OH6", n, p_bep)
tested_overall, tested_discrete = Q_(3.84, "mm/s"), Q_(2.24, "mm/s")
print("12th:", lim12["overall"], lim12["filtered"], "|", lim12["basis"])
print("8th: ", lim8["overall"], lim8["filtered"])
display(Image(data=plot_high_speed_chart(HighSpeedRule(), n, p_bep,
                                         title="OH6 at 10 212 r/min (12th edition rule)")))
"""),
        md(r"""
## The whole verdict at once

The workbench's Compliance node and `PerformanceChecker` use one engine,
`evaluate_performance`.  Every row is `pass`, `fail`, `info` (efficiency without a
purchaser tolerance) or `not evaluated`; a verdict with a `not evaluated` row is
**NOT FULLY ASSESSED**, never an approval.  Here with the exercise numbers and a curve
that cannot predict power (no power column was recorded):
"""),
        code(r"""
from pump.acceptance import evaluate_performance

class TrainingCurve:
    points = ()
    def __init__(self, with_power=True):
        self.with_power = with_power
    def predict_head(self, q):
        return Q_(357.0 - 0.18 * q.to("m**3/h").magnitude ** 2, "m")
    def predict_breaking_power(self, q):
        if not self.with_power:
            raise AttributeError("no power column")
        return Q_(24.6, "kW")
    def predict_efficiency(self, q):
        return Q_(31.5, "percent")

def show(v):
    for r in v.rows:
        dev = f"{r.deviation:+.2%}" if r.deviation is not None else "-"
        print(f"  {r.name:12s} {r.status:14s} {dev:>8s}  {r.note}")
    print("  ->", "APPROVED" if v.approved else
          ("NOT FULLY ASSESSED" if v.passed else "NOT APPROVED"))

kw = dict(rated_power=Q_(26.9, "kW"), rated_efficiency=Q_(32.7, "percent"),
          rated_speed=Q_(10212, "rpm"), test_speeds=(Q_(10301, "rpm"),))
full = evaluate_performance(TrainingCurve(), rated_q, rated_h, p9001, **kw)
partial = evaluate_performance(TrainingCurve(False), rated_q, rated_h, p9001, **kw)
print("complete test data:"); show(full)
print("no power column:"); show(partial)
"""),
        md(r"""
## Exercise 11 · Shut-off not tested (integral-gear OH6)

API 610 12th 8.3.3.4 suggests not running a pump at shut-off when its power density
PD = P / (D_imp · D_nozzle²) exceeds about 13 MW/m³ (0.286 hp/in³).  The case of TR-01
§4.1: 26.9 kW, impeller 125.5 mm, 2 in discharge.  Its shut-off head can only be
extrapolated (lowest test point at 35 % of rated flow), and three reasonable fits give
three different verdicts against the 357.4 m datasheet value.
"""),
        code(r"""
pd = (Q_(26.9, "kW") / (Q_(125.5, "mm") * Q_(2, "in") ** 2)).to("MW/m**3")
pd_us = pd.to("hp/in**3")
print(f"PD = {pd:.1f~P} = {pd_us:.2f~P}  ({pd.magnitude / 13:.1f} x the 13 MW/m3 guide)")

rated_so11 = Q_(357.4, "m")
lo11, hi11 = api8.shutoff_tolerance(Q_(333.8, "m"))
fits = {"cubic, all points": 743.0, "cubic, no run-out": 364.8, "quadratic, no run-out": 312.2}
verdicts = {}
for name, h0 in fits.items():
    d = deviation(rated_so11, Q_(h0, "m"))
    verdicts[name] = -lo11 <= d <= hi11
    print(f"{name:22s} H(0) = {h0:6.1f} m  {d:+.1%}  {'pass' if verdicts[name] else 'fail'}")
"""),
        md(r"""
## Exercise 12 · Bearing oil temperatures by lubrication system

The temperature rules depend on the lubrication system stated in the log (11th
6.10.2.4): pressurized, the oil rise through each bearing (outlet − inlet) ≤ 28 K;
ring-oil / splash, the sump rise above the test-cell ambient ≤ 40 K (39 K in the 12th).
"""),
        code(r"""
from pump.mechanical_run import Channel, RunReading, MechanicalRunLog, MechanicalRunChecker

times = [f"{6 + i // 4:02d}:{15 * (i % 4):02d}" for i in range(17)]

def run(lube, values, key="api610:11"):
    chans = [Channel(n, r, loc) for n, (r, loc, _v) in values.items()]
    reads = [RunReading(t, {n: Q_(v, "degC") for n, (_r, _l, v) in values.items()})
             for t in times]
    crit = AcceptanceCriteria.load(key).mechanical_run
    return MechanicalRunChecker(MechanicalRunLog(chans, reads, lubrication=lube), crit).check()

press = run("pressurized", {"Oil inlet": ("oil_inlet_temperature", "", 41.0),
                            "Oil out DE": ("oil_outlet_temperature", "DE", 63.0),
                            "Oil out NDE": ("oil_outlet_temperature", "NDE", 71.0)})
ring = {"Sump": ("oil_temperature", "", 66.0), "Ambient": ("ambient_temperature", "", 25.0)}
ring11, ring12 = run("ring_oil", ring), run("ring_oil", ring, "api610:12")
no_inlet = run("pressurized", {"Oil out DE": ("oil_outlet_temperature", "DE", 63.0)})
for label, run_res in (("(a) pressurized", press), ("(b) ring-oil 11th", ring11),
                       ("(b) ring-oil 12th", ring12), ("(c) no inlet", no_inlet)):
    for r in run_res.rules:
        print(f"{label:18s} {r.name:40s} {r.value if r.value is None else f'{r.value:.1f~P}'!s:>8} "
              f"limit {r.limit:.0f~P}  {r.status}")
"""),
        md("## Answers (asserted)"),
        code(r"""
assert de.rated == (2.1, 3.0) and de.por == (2.6, 3.0) and de.aor == (3.4, 3.9)
assert abs(lim12["overall"].magnitude - 4.1) < 1e-9 and abs(lim12["filtered"].magnitude - 2.7) < 1e-9
assert tested_overall <= lim12["overall"] and tested_discrete <= lim12["filtered"]
assert tested_overall > lim8["overall"] and tested_discrete > lim8["filtered"]
assert full.approved and full.row("Efficiency").status == "info"
assert not partial.approved and partial.passed and partial.not_evaluated == ("Power",)

assert ex1["8th head"] == (0.02, 0.05) and ex1["8th shut-off"] == (0.10, 0.10)
assert ex1["11th head"] == (0.03, 0.03) and ex1["11th shut-off"] == (0.08, 0.08)

assert head_ok and abs(dh - 0.0171) < 5e-4 and api11.head_tolerance(rated_h) == (0.03, 0.03)
assert power_ok and abs(dp + 0.0855) < 5e-4
assert p9001.efficiency_tol_minus is None  # efficiency: information only
assert res.status == "fail" and res.quoted_ok is False and needs_all_points
assert abs(v.magnitude - 4.064) < 1e-3 and vib_fails_if_rms
assert speed_ok and abs(dn - 0.00872) < 1e-4

assert abs(drooping(rated_q).magnitude - 333.8) < 0.01
assert head_rises_to_shutoff(rising, rated_q)
assert not head_rises_to_shutoff(drooping, rated_q)
# the drooping curve's shut-off is 3 % below 345 m: inside +/-5 %, yet it fails the rule
so_dev = deviation(rated_so, drooping(Q_(0, "m**3/h")))
assert abs(so_dev + 0.03) < 1e-3
lo, hi = api8.shutoff_tolerance(Q_(333.8, "m"))
assert -lo <= so_dev <= hi

assert 80 < pd.magnitude < 86 and 1.7 < pd_us.magnitude < 1.9  # about 6x the guide
assert pd > Q_(13, "MW/m**3") and pd_us > Q_(0.286, "hp/in**3")
# the extrapolated shut-off verdict depends on the fit, not on the pump
assert sorted(verdicts.values()) == [False, False, True]
rise = next(r for r in press.rules if r.key == "oil_rise_max")
assert rise.status == "fail" and abs(rise.value.magnitude - 30.0) < 1e-9
assert next(r for r in press.rules if r.key == "oil_outlet_design_max").status == "info"
for ring_res, lim in ((ring11, 40), (ring12, 39)):
    sump = next(r for r in ring_res.rules if r.key == "sump_rise_max")
    assert sump.status == "fail" and sump.limit.magnitude == lim
assert next(r for r in no_inlet.rules if r.key == "oil_rise_max").status == "not evaluated"
assert not no_inlet.fully_assessed
print("TR-01 answers OK")
"""),
    ]


# --------------------------------------------------------------------------- #
NOTEBOOKS = {
    "UC-01_selection": uc01,
    "UC-02_performance_verification": uc02,
    "UC-03-04_system_operating_point": uc0304,
    "UC-05_npsh": uc05,
    "UC-07_trim": uc07,
    "UC-08_compare": uc08,
    "UC-09_reports": uc09,
    "UC-11_mechanical_run": uc11,
    "viscosity_HI967": viscosity,
    "TR-01_witness_training": tr01,
}


def main():
    for name, builder in NOTEBOOKS.items():
        path = write(name, builder())
        print("wrote", path.relative_to(HERE.parent))


if __name__ == "__main__":
    main()
