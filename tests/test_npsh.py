"""
NPSH margin (UC-05): NPSHa, NPSH3 sweep, NPSHr curve, margin / check, the
legacy ``NPSH_available`` alias and the shipped (not configured) criteria.
"""

import math
from io import BytesIO

import pytest

from pump import Q_, DesignPoint
from pump.acceptance import AcceptanceCriteria
from pump.npsh import (
    NPSHCriteria,
    NPSHrCurve,
    check_npsh,
    npsh3_from_sweep,
    npsh_available,
    npsh_margin,
    plot_npsh,
)
from pump.utilities.fluid import Water
from pump.utilities.pressure import Pressure

G = 9.80665

# B-34004A Sundyne p.2: NPSHR [ft] at Q [gpm]
B34004A = [(15.2, 2.7), (29.4, 2.9), (34.8, 3.3), (43.5, 4.1), (47.9, 3.3)]
RATED_GPM = 43.1


def _b34004a_curve():
    return NPSHrCurve(
        tuple(Q_(q, "gallon/minute") for q, _ in B34004A),
        tuple(Q_(h, "ft") for _, h in B34004A),
    )


# --------------------------------------------------------------------------- #
# NPSH available
# --------------------------------------------------------------------------- #
def _hand_npsha(water):
    rho = water.density.to("kg/m**3").magnitude
    pv = water.vapour_pressure.to("Pa").magnitude
    velocity = (50.0 / 3600.0) / (math.pi * 0.1**2 / 4)
    return (120000.0 - pv) / (rho * G) + velocity**2 / (2 * G)


def test_npsha_hand_case_absolute():
    water = Water(Q_(20, "degC"))
    result = npsh_available(
        Pressure(Q_(1.2, "bar"), "a"),
        water,
        Q_(50, "m**3/h"),
        suction_id=Q_(100, "mm"),
        z_suction=Q_(0, "m"),
    )
    assert result.to("m").magnitude == pytest.approx(_hand_npsha(water), rel=1e-9)
    assert 11.5 < result.to("m").magnitude < 12.5


def test_npsha_gauge_equals_absolute():
    water = Water(Q_(20, "degC"))
    kwargs = dict(suction_id=Q_(100, "mm"), z_suction=Q_(0, "m"))
    absolute = npsh_available(
        Pressure(Q_(1.2, "bar"), "a"), water, Q_(50, "m**3/h"), **kwargs
    )
    gauge = npsh_available(
        Pressure(Q_(0.18675, "bar"), "g"), water, Q_(50, "m**3/h"), **kwargs
    )
    assert gauge.to("m").magnitude == pytest.approx(
        absolute.to("m").magnitude, rel=1e-9
    )


def test_npsha_elevation_and_no_diameter():
    water = Water(Q_(20, "degC"))
    p = Pressure(Q_(1.2, "bar"), "a")
    base = npsh_available(p, water, Q_(50, "m**3/h"))
    raised = npsh_available(p, water, Q_(50, "m**3/h"), z_suction=Q_(2, "m"))
    assert raised.to("m").magnitude == pytest.approx(base.to("m").magnitude + 2.0)
    # No suction ID: no velocity head.
    rho = water.density.to("kg/m**3").magnitude
    pv = water.vapour_pressure.to("Pa").magnitude
    assert base.to("m").magnitude == pytest.approx(
        (120000.0 - pv) / (rho * G), rel=1e-9
    )


def test_npsha_requires_vapour_pressure(water):
    p = Pressure(Q_(1.2, "bar"), "a")
    with pytest.raises(ValueError, match="vapour pressure"):
        npsh_available(p, water, Q_(50, "m**3/h"))
    ok = npsh_available(p, water, Q_(50, "m**3/h"), vapour_pressure=Q_(2.3, "kPa"))
    assert ok.to("m").magnitude > 0


def test_npsha_rejects_bare_pressure():
    with pytest.raises(ValueError):
        npsh_available(Q_(1.2, "bar"), Water(Q_(20, "degC")), Q_(50, "m**3/h"))


# --------------------------------------------------------------------------- #
# NPSH3 from a sweep
# --------------------------------------------------------------------------- #
def test_npsh3_sweep_known_knee():
    # Flat 100 m down to NPSHa = 6 m, then dropping 10 m per metre of NPSHa.
    npsha = [Q_(v, "m") for v in (8, 7, 6, 5, 4, 3)]
    heads = [Q_(v, "m") for v in (100, 100, 100, 90, 80, 70)]
    # 97 m target is reached 0.3 m below the knee at 6 m.
    assert npsh3_from_sweep(npsha, heads).to("m").magnitude == pytest.approx(5.7)


def test_npsh3_sweep_unsorted_and_custom_drop():
    npsha = [Q_(v, "m") for v in (3, 8, 5, 7, 4, 6)]
    heads = [Q_(v, "m") for v in (70, 100, 90, 100, 80, 100)]
    assert npsh3_from_sweep(npsha, heads).to("m").magnitude == pytest.approx(5.7)
    assert npsh3_from_sweep(npsha, heads, drop=0.10).to("m").magnitude == pytest.approx(
        5.0
    )


def test_npsh3_sweep_never_drops():
    npsha = [Q_(v, "m") for v in (8, 7, 6, 5)]
    heads = [Q_(100, "m")] * 4
    with pytest.raises(ValueError, match="never dropped"):
        npsh3_from_sweep(npsha, heads)


def test_npsh3_sweep_validates_input():
    with pytest.raises(ValueError):
        npsh3_from_sweep([Q_(1, "m")] * 3, [Q_(1, "m")] * 2)
    with pytest.raises(ValueError):
        npsh3_from_sweep([Q_(2, "m"), Q_(1, "m")], [Q_(1, "m")] * 2)


# --------------------------------------------------------------------------- #
# NPSHr curve
# --------------------------------------------------------------------------- #
def test_npshr_polynomial_and_extrapolation():
    def f(x):
        return 2 + 0.01 * x + 0.00001 * x * x

    xs = (0, 100, 200, 300)
    curve = NPSHrCurve(
        tuple(Q_(x, "m**3/h") for x in xs), tuple(Q_(f(x), "m") for x in xs)
    )
    assert curve(Q_(150, "m**3/h")).to("m").magnitude == pytest.approx(f(150))
    assert curve.at_rated(Q_(250, "m**3/h")).to("m").magnitude == pytest.approx(f(250))
    assert not curve.extrapolated(Q_(150, "m**3/h"))
    assert not curve.extrapolated(Q_(300, "m**3/h"))
    assert curve.extrapolated(Q_(350, "m**3/h"))
    assert curve.extrapolated(Q_(-10, "m**3/h"))


def test_npshr_degree_reduced_for_few_points():
    curve = NPSHrCurve((Q_(0, "m**3/h"), Q_(100, "m**3/h")), (Q_(1, "m"), Q_(2, "m")))
    assert curve(Q_(50, "m**3/h")).to("m").magnitude == pytest.approx(1.5)


def test_npshr_curve_is_unit_aware():
    curve = NPSHrCurve((Q_(0, "m**3/h"), Q_(100, "m**3/h")), (Q_(1, "m"), Q_(2, "m")))
    q = Q_(100, "m**3/h").to("gallon/minute")
    assert curve(q).to("m").magnitude == pytest.approx(2.0)


def test_npshr_curve_validates():
    with pytest.raises(ValueError):
        NPSHrCurve((), ())
    with pytest.raises(ValueError):
        NPSHrCurve((Q_(1, "m**3/h"),), (Q_(1, "m"), Q_(2, "m")))


# --------------------------------------------------------------------------- #
# Margin and check
# --------------------------------------------------------------------------- #
def test_margin_and_ratio():
    m = npsh_margin(Q_(2.4, "m"), Q_(1.2, "m"))
    assert m["ratio"] == pytest.approx(2.0)
    assert m["margin"].to("m").magnitude == pytest.approx(1.2)
    m2 = npsh_margin(Q_(3.0, "m"), Q_(3.937, "ft"))  # same length, mixed units
    assert m2["ratio"] == pytest.approx(3.0 / (3.937 * 0.3048))


def test_check_without_criteria_is_info():
    res = check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), NPSHCriteria())
    assert res.status == "info"
    assert res.ratio == pytest.approx(2.0)
    assert res.margin.to("m").magnitude == pytest.approx(1.2)
    assert res.verified is False
    assert check_npsh(Q_(2.4, "m"), Q_(1.2, "m")).status == "info"


def test_check_with_criteria_pass_and_fail():
    ok = check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), NPSHCriteria(min_ratio=1.5))
    assert ok.status == "pass"
    bad = check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), NPSHCriteria(min_ratio=2.5))
    assert bad.status == "fail"
    margin_bad = check_npsh(
        Q_(2.4, "m"), Q_(1.2, "m"), NPSHCriteria(min_margin=Q_(2.0, "m"))
    )
    assert margin_bad.status == "fail"
    # Either configured rule failing fails the check.
    mixed = check_npsh(
        Q_(2.4, "m"),
        Q_(1.2, "m"),
        NPSHCriteria(min_ratio=1.5, min_margin=Q_(2.0, "m"), verified=True),
    )
    assert mixed.status == "fail" and mixed.verified is True


def test_api_editions_have_no_margin_rule_but_rated_npsh_plus_zero():
    # API 610 sets no NPSHa/NPSHr margin (that is the client's), only "Rated NPSH +0 %".
    for key, _label in AcceptanceCriteria.available():
        crit = AcceptanceCriteria.load(key)
        assert crit.npsh.min_ratio is None and crit.npsh.min_margin is None
        assert not crit.npsh.configured
        assert crit.npsh.npshr_tol_plus == 0.0


def test_quoted_npshr_rule():
    rule = NPSHCriteria(npshr_tol_plus=0.0)
    over = check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), rule, npshr_quoted=Q_(1.1, "m"))
    assert over.status == "fail" and over.quoted_ok is False
    ok = check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), rule, npshr_quoted=Q_(1.2, "m"))
    assert ok.status == "pass" and ok.quoted_ok is True
    # No quoted value: nothing to judge.
    assert check_npsh(Q_(2.4, "m"), Q_(1.2, "m"), rule).status == "info"


def test_criteria_from_table():
    crit = NPSHCriteria.from_table(
        {"min_ratio": 1.3, "min_margin": "0.6 m", "verified": True, "source": "x"}
    )
    assert crit.min_ratio == 1.3 and crit.min_margin.to("m").magnitude == 0.6
    assert crit.verified and crit.source == "x" and crit.configured


# --------------------------------------------------------------------------- #
# Plot
# --------------------------------------------------------------------------- #
def test_plot_npsh_returns_png():
    curve = _b34004a_curve()
    buf = plot_npsh(curve, Q_(2.4, "m"), Q_(RATED_GPM, "gallon/minute"))
    assert isinstance(buf, BytesIO)
    assert buf.read(8) == b"\x89PNG\r\n\x1a\n"
    assert plot_npsh(curve, None, None).getvalue().startswith(b"\x89PNG")


# --------------------------------------------------------------------------- #
# Legacy alias
# --------------------------------------------------------------------------- #
def test_npsh_available_alias_warns_and_sets_npsha(water):
    with pytest.warns(DeprecationWarning, match="NPSH_available"):
        dp = DesignPoint(
            fluid=water,
            capacity=Q_(833, "m**3/h"),
            differential_head=Q_(73, "m"),
            NPSH_available=Q_(5, "m"),
        )
    assert dp.npsha.to("m").magnitude == pytest.approx(5.0)
    assert not hasattr(dp, "NPSH_available")


def test_npsha_kwarg_does_not_warn(water):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        dp = DesignPoint(
            fluid=water,
            capacity=Q_(833, "m**3/h"),
            differential_head=Q_(73, "m"),
            npsha=Q_(5, "m"),
        )
    assert dp.npsha.to("m").magnitude == pytest.approx(5.0)


# --------------------------------------------------------------------------- #
# B-34004A reference case
# --------------------------------------------------------------------------- #
def test_b34004a_npshr_at_rated_and_ratio():
    curve = _b34004a_curve()
    rated = Q_(RATED_GPM, "gallon/minute")
    npshr = curve.at_rated(rated)
    assert not curve.extrapolated(rated)
    assert 3.4 <= npshr.to("ft").magnitude <= 4.2  # roughly 3.5-4.1 ft
    result = check_npsh(Q_(2.4, "m"), npshr, NPSHCriteria())
    assert result.ratio > 1.9
    assert result.status == "info"
