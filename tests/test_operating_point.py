"""Operating point (UC-04): pump curve ∩ system curve, bisection, flags, errors."""

import pytest

from pump import Q_, Fluid, PerformanceCurve, SystemCurve, TestPoint
from pump.fitting import bisect_root
from pump.operating_point import operating_point

K2 = "m/(m**3/h)**2"
WATER = Fluid("Water", density=Q_(997, "kg/m**3"))


def _curve(qs, a=100.0, b=0.004, degree=2):
    pts = [
        TestPoint(
            fluid=WATER,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=Q_(1750, "rpm"),
            _head=Q_(a - b * q * q, "m"),
            breaking_power=Q_(200.0 + 0.1 * q, "kW"),
        )
        for q in qs
    ]
    return PerformanceCurve(WATER, pts, polynomial_degree=degree)


def test_bisect_root_basic_and_sign_error():
    assert bisect_root(lambda x: x * x - 4.0, 0.0, 5.0) == pytest.approx(2.0, abs=1e-9)
    assert bisect_root(lambda x: x - 1.0, 1.0, 3.0) == 1.0  # root at an end
    with pytest.raises(ValueError):
        bisect_root(lambda x: x * x + 1.0, -1.0, 1.0)


def test_analytic_intersection_to_1e6():
    curve = _curve(range(0, 101, 20))
    # 100 - 0.004 Q^2 = 50 + 0.002 Q^2   ->   Q = sqrt(50 / 0.006)
    system = SystemCurve(Q_(50, "m"), Q_(0.002, K2))
    op = operating_point(curve, system)
    q_exact = (50.0 / 0.006) ** 0.5
    assert op.q.to("m**3/h").magnitude == pytest.approx(q_exact, abs=1e-6)
    assert op.h.to("m").magnitude == pytest.approx(50.0 + 0.002 * q_exact**2, abs=1e-6)
    assert op.extrapolated is False
    assert op.power is not None
    assert op.power.to("kW").magnitude == pytest.approx(200.0 + 0.1 * q_exact, rel=1e-6)


def test_extrapolation_flag():
    curve = _curve(range(0, 61, 10))
    system = SystemCurve(Q_(70, "m"), Q_(0.002, K2))
    op = operating_point(curve, system)  # root ~ 70.7 > 60 tested
    assert op.q.to("m**3/h").magnitude == pytest.approx((30.0 / 0.006) ** 0.5, abs=1e-6)
    assert op.extrapolated is True


def test_no_intersection_raises():
    curve = _curve(range(0, 101, 20))
    with pytest.raises(ValueError, match="intersect"):
        operating_point(curve, SystemCurve(Q_(150, "m"), Q_(0.002, K2)))


def test_spline_method_close_to_poly():
    curve = _curve(range(0, 101, 10))
    system = SystemCurve(Q_(50, "m"), Q_(0.002, K2))
    op = operating_point(curve, system, method="spline")
    assert op.q.to("m**3/h").magnitude == pytest.approx((50.0 / 0.006) ** 0.5, rel=1e-2)
    assert op.extrapolated is False


def test_bad_method_raises():
    curve = _curve(range(0, 101, 20))
    with pytest.raises(ValueError):
        operating_point(curve, SystemCurve(Q_(50, "m"), Q_(0.002, K2)), method="cubic")


def test_mathx_reexport_is_the_library_class():
    from pump.fitting import NaturalCubicSpline, r_squared
    from pumpflow import mathx

    assert mathx.NaturalCubicSpline is NaturalCubicSpline
    assert mathx.r_squared is r_squared
    assert round(float(NaturalCubicSpline([0, 1, 2, 3], [0, 1, 4, 9])(1.5)), 3) == 2.2
