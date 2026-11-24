"""API 610 Annex M style charts: test curve format (Fig. M.3) and test points
with vibration against flow (Fig. M.4)."""

import pytest

from pump import Q_, PerformanceCurve, TestPoint, Water
from pump.npsh import NPSHrCurve
from pump.utilities.annex_m_charts import (
    _nice_range,
    plot_annex_m_curve,
    plot_test_points_vibration,
)

PNG = b"\x89PNG"


@pytest.fixture(scope="module")
def curve():
    water = Water(temperature=Q_(20, "degC"))
    rows = [(0.0, 120, 18), (60, 116, 30), (120, 108, 41), (180, 94, 52), (240, 72, 60)]
    pts = []
    for q, h, p in rows:
        eff = 0.0 if q == 0 else (1000 * 9.80665 * q / 3600 * h) / (p * 1000) * 100
        pts.append(
            TestPoint(
                fluid=water,
                capacity=Q_(q, "m**3/h"),
                speed=Q_(2950, "rpm"),
                _head=Q_(h, "m"),
                breaking_power=Q_(p, "kW"),
                _efficiency=Q_(eff, "percent"),
            )
        )
    return PerformanceCurve(water, pts, polynomial_degree=3)


def test_nice_range_encloses_values():
    lo, hi, ticks = _nice_range([72.0, 121.0])
    assert lo <= 72.0 and hi >= 121.0
    assert ticks[0] == lo and ticks[-1] == hi


def test_m3_curve_with_and_without_npsh(curve):
    npsh = NPSHrCurve(
        tuple(Q_(q, "m**3/h") for q in (60, 120, 180, 240)),
        tuple(Q_(v, "m") for v in (4.0, 4.6, 6.3, 9.5)),
    )
    rated = {
        "q": Q_(180, "m**3/h"),
        "head": Q_(94, "m"),
        "power": Q_(55.9, "kW"),
        "efficiency": Q_(82.3, "percent"),
        "npsh3": Q_(6.3, "m"),
    }
    por = (Q_(126, "m**3/h"), Q_(216, "m**3/h"))
    full = plot_annex_m_curve(
        curve,
        rated,
        por=por,
        aor=(Q_(60, "m**3/h"), Q_(240, "m**3/h")),
        npsh_curve=npsh,
        header={"serial": "X-1", "curve_no": "C-7"},
        impeller={"max": Q_(300, "mm"), "rated": Q_(290, "mm")},
        date="2026-11-17",
        head_band=(-0.02, 0.05),
    )
    bare = plot_annex_m_curve(curve, {"q": rated["q"], "head": rated["head"]})
    assert full.startswith(PNG) and bare.startswith(PNG)


def test_m4_points_and_vibration(curve):
    vib = tuple(
        (Q_(q, "m**3/h"), {"vib_de": Q_(v, "mm/s"), "vib_de_f": Q_(v * 0.6, "mm/s")})
        for q, v in ((0, 1.0), (60, 3.1), (120, 2.4), (180, 2.2), (240, 3.5))
    )
    limits = {"overall": Q_(3.0, "mm/s"), "filtered": Q_(2.0, "mm/s")}
    por = (Q_(126, "m**3/h"), Q_(216, "m**3/h"))
    for measure in ("overall", "filtered"):
        png = plot_test_points_vibration(
            curve, Q_(180, "m**3/h"), Q_(94, "m"), vib, limits, por=por, measure=measure
        )
        assert png.startswith(PNG)
    # no vibration at all still draws the head curve and test points
    assert plot_test_points_vibration(
        curve, Q_(180, "m**3/h"), Q_(94, "m"), (), limits
    ).startswith(PNG)
