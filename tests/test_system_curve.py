"""System curve (UC-03): H = H_static + k·Q^n, two-point fit, Darcy–Weisbach pipe."""

import math

import numpy as np
import pytest

from pump import Q_, SystemCurve, Water, Fluid
from pump.system_curve import PipeSystemCurve

K2 = "m/(m**3/h)**2"


def test_head_static_plus_k():
    s = SystemCurve(Q_(20, "m"), Q_(1e-4, K2))
    assert s.head(Q_(0, "m**3/h")).to("m").magnitude == pytest.approx(20.0)
    assert s.head(Q_(100, "m**3/h")).to("m").magnitude == pytest.approx(21.0)


def test_curve_returns_quantity_array():
    s = SystemCurve(Q_(20, "m"), Q_(1e-4, K2))
    out = s.curve(Q_(np.array([0.0, 100.0, 200.0]), "m**3/h"))
    assert np.allclose(out.to("m").magnitude, [20.0, 21.0, 24.0])


def test_from_points_recovers_k():
    ref = SystemCurve(Q_(12.5, "m"), Q_(3.0e-5, K2))
    p1 = (Q_(100, "m**3/h"), ref.head(Q_(100, "m**3/h")))
    p2 = (Q_(400, "m**3/h"), ref.head(Q_(400, "m**3/h")))
    s = SystemCurve.from_points(p1, p2)
    assert s.static_head.to("m").magnitude == pytest.approx(12.5, rel=1e-9)
    assert s.k.magnitude == pytest.approx(3.0e-5, rel=1e-9)


def test_from_points_other_exponent():
    ref = SystemCurve(Q_(5.0, "m"), Q_(2.0e-3, "m/(m**3/h)**1.8"), 1.8)
    p1 = (Q_(50, "m**3/h"), ref.head(Q_(50, "m**3/h")))
    p2 = (Q_(150, "m**3/h"), ref.head(Q_(150, "m**3/h")))
    s = SystemCurve.from_points(p1, p2, exponent=1.8)
    assert s.k.magnitude == pytest.approx(2.0e-3, rel=1e-9)
    assert s.static_head.to("m").magnitude == pytest.approx(5.0, rel=1e-9)


def test_unit_mixing_gpm_ft_identical():
    si = SystemCurve.from_points(
        (Q_(100, "m**3/h"), Q_(11, "m")), (Q_(200, "m**3/h"), Q_(14, "m"))
    )
    us = SystemCurve.from_points(
        (Q_(100, "m**3/h").to("gallon/min"), Q_(11, "m").to("ft")),
        (Q_(200, "m**3/h").to("gallon/min"), Q_(14, "m").to("ft")),
    )
    assert us.k.magnitude == pytest.approx(si.k.magnitude, rel=1e-9)
    assert us.static_head.to("m").magnitude == pytest.approx(
        si.static_head.to("m").magnitude, rel=1e-9
    )
    q = Q_(250, "m**3/h")
    assert us.head(q.to("gallon/min")).to("m").magnitude == pytest.approx(
        si.head(q).to("m").magnitude, rel=1e-9
    )
    # k given in US units is normalised to m/(m3/h)^2
    k_us = Q_(1e-4, K2).to("ft/(gallon/min)**2")
    assert SystemCurve(Q_(20, "m").to("ft"), k_us).k.magnitude == pytest.approx(1e-4)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        SystemCurve(Q_(20, "m"), Q_(1e-4, "m"))  # k has wrong dimensions
    with pytest.raises(ValueError):
        SystemCurve(Q_(20, "kg"), Q_(1e-4, K2))
    with pytest.raises(ValueError):
        SystemCurve(Q_(20, "m"), Q_(1e-4, K2), exponent=0.0)
    with pytest.raises(ValueError):
        SystemCurve.from_points(
            (Q_(100, "m**3/h"), Q_(11, "m")), (Q_(100, "m**3/h"), Q_(14, "m"))
        )


def _hand_pipe_head(q_m3h, static=15.0, length=100.0, d=0.1, eps=0.045e-3, k_minor=0.0):
    """Darcy–Weisbach + Swamee–Jain, written out independently of the library."""
    nu = Water(Q_(20, "degC")).kinematic_viscosity.to("m**2/s").magnitude
    v = (q_m3h / 3600.0) / (math.pi * d * d / 4.0)
    re = v * d / nu
    f = 0.25 / math.log10(eps / (3.7 * d) + 5.74 / re**0.9) ** 2
    return static + (f * length / d + k_minor) * v * v / (2 * 9.80665)


def test_from_pipe_matches_hand_darcy_weisbach():
    water = Water(Q_(20, "degC"))
    s = SystemCurve.from_pipe(
        Q_(15, "m"), Q_(100, "m"), Q_(100, "mm"), Q_(0.045, "mm"), water
    )
    assert isinstance(s, PipeSystemCurve)
    got = s.head(Q_(50, "m**3/h")).to("m").magnitude
    assert got == pytest.approx(_hand_pipe_head(50.0), rel=1e-9)
    assert s.head(Q_(0, "m**3/h")).to("m").magnitude == pytest.approx(15.0)


def test_from_pipe_minor_losses_and_curve():
    water = Water(Q_(20, "degC"))
    s = SystemCurve.from_pipe(
        Q_(15, "m"),
        Q_(100, "m"),
        Q_(100, "mm"),
        Q_(0.045, "mm"),
        water,
        minor_k_sum=5.0,
    )
    qs = Q_(np.array([20.0, 50.0, 80.0]), "m**3/h")
    out = s.curve(qs).to("m").magnitude
    expect = [_hand_pipe_head(q, k_minor=5.0) for q in (20.0, 50.0, 80.0)]
    assert np.allclose(out, expect, rtol=1e-9)


def test_from_pipe_unit_mixing_identical():
    water = Water(Q_(20, "degC"))
    si = SystemCurve.from_pipe(
        Q_(15, "m"), Q_(100, "m"), Q_(100, "mm"), Q_(0.045, "mm"), water
    )
    us = SystemCurve.from_pipe(
        Q_(15, "m").to("ft"),
        Q_(100, "m").to("ft"),
        Q_(100, "mm").to("inch"),
        Q_(0.045, "mm").to("inch"),
        water,
    )
    q = Q_(50, "m**3/h")
    assert us.head(q.to("gallon/min")).to("m").magnitude == pytest.approx(
        si.head(q).to("m").magnitude, rel=1e-9
    )


def test_from_pipe_manual_fluid_kinematic_viscosity():
    fl = Fluid("Oil", density=Q_(850, "kg/m**3"), viscosity=Q_(20, "cSt"))
    s = SystemCurve.from_pipe(
        Q_(0, "m"), Q_(100, "m"), Q_(100, "mm"), Q_(0.045, "mm"), fl
    )
    # 20 cSt at 50 m3/h is laminar-to-transitional (Re ~ 8.8e3): friction is
    # larger than for water.
    water = SystemCurve.from_pipe(
        Q_(0, "m"), Q_(100, "m"), Q_(100, "mm"), Q_(0.045, "mm"), Water(Q_(20, "degC"))
    )
    q = Q_(50, "m**3/h")
    assert s.head(q).magnitude > water.head(q).magnitude


def test_pipe_equivalent_k_matches_at_reference():
    water = Water(Q_(20, "degC"))
    s = SystemCurve.from_pipe(
        Q_(15, "m"),
        Q_(100, "m"),
        Q_(100, "mm"),
        Q_(0.045, "mm"),
        water,
        q_ref=Q_(50, "m**3/h"),
    )
    eq = s.equivalent()
    q = Q_(50, "m**3/h")
    assert eq.head(q).to("m").magnitude == pytest.approx(
        s.head(q).to("m").magnitude, rel=1e-9
    )
    with pytest.raises(ValueError):
        SystemCurve.from_pipe(
            Q_(15, "m"), Q_(100, "m"), Q_(100, "mm"), Q_(0.045, "mm"), water
        ).equivalent()
