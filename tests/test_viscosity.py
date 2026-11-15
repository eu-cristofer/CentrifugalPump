"""
Sprint 9 — viscosity correction (HI 9.6.7 / ISO TR 17766).

There is no freely available official worked example (the HI and ISO texts are
paid), so the method is pinned by independent checks:

1. the published US (26.6) and SI (16.5) constants agree for the same pump;
2. continuity at B = 1;
3. agreement with the legacy HI chart field example (500 gpm, ~648 cSt, 150 ft);
4. hand values of the closed forms;
5. B >= 40 warns but still returns the factors;
6. ``to_viscous`` returns a new object and leaves the original unchanged;
7. B < 1 (water-like / B-34004A at 0.52 cSt) leaves the curve bit-identical.

Equation source: ANSI/HI 9.6.7-2010 Eq. 2-7 as reproduced by
midstreamcalculator.com; NOT cross-checked against the standard text.

The ``water`` fixture comes from ``tests/conftest.py``.
"""

import warnings

import pytest

from pump import Q_, Fluid, Pressure, TestPoint, PerformanceCurve
from pump.constants import G
from pump.utilities.report import LocalizationHelper, viscosity_sentence
from pump.viscosity import b_parameter, correction_factors

from pumpflow.binding import correct_curve
from pumpflow.signals import RatedPoint, TestPointSet, TestRow


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def eff_curve(water):
    """Water curve with efficiency pinned (no shut-off point), 1750 rpm."""
    rows = [  # (capacity m3/h, head m, efficiency %)
        (60, 58, 35),
        (120, 54, 55),
        (180, 47, 62),
        (240, 37, 55),
        (300, 25, 35),
    ]
    points = []
    for q, h, eta in rows:
        power_kw = 997.0 * 9.80665 * (q / 3600.0) * h / (eta / 100.0) / 1000.0
        points.append(
            TestPoint(
                fluid=water,
                capacity=Q_(q, "m**3/h"),
                speed_of_rotation=Q_(1750, "rpm"),
                _head=Q_(h, "m"),
                _efficiency=Q_(eta, "percent"),
                breaking_power=Q_(power_kw, "kW"),
            )
        )
    return PerformanceCurve(water, points, polynomial_degree=4)


@pytest.fixture
def oil():
    return Fluid("Oil", density=Q_(950, "kg/m**3"), viscosity=Q_(500, "cSt"))


@pytest.fixture
def light():
    return Fluid("Light", density=Q_(900, "kg/m**3"), viscosity=Q_(1, "cSt"))


# --------------------------------------------------------------------------- #
# 1. US and SI constants agree
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "nu_cst, h_m, q_m3h, n_rpm",
    [
        (100, 50, 200, 1750),
        (647, 45.72, 113.56, 1750),
        (1000, 100, 50, 3550),
        (20, 333.8, 9.8, 10212),
    ],
)
def test_us_and_si_constants_agree(nu_cst, h_m, q_m3h, n_rpm):
    b_us = b_parameter(
        Q_(nu_cst, "cSt"), Q_(q_m3h, "m**3/h"), Q_(h_m, "m"), Q_(n_rpm, "rpm")
    )
    b_si = 16.5 * nu_cst**0.5 * h_m**0.0625 / (q_m3h**0.375 * n_rpm**0.25)
    assert b_us == pytest.approx(b_si, rel=0.005)


# --------------------------------------------------------------------------- #
# 2. Continuity at B = 1
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("b", [0.1, 0.5, 1.0])
def test_no_correction_for_b_at_most_one(b):
    assert correction_factors(b) == (1.0, 1.0, 1.0)
    assert correction_factors(b, 0.6) == (1.0, 1.0, 1.0)


def test_factors_approach_one_just_above_one():
    for c in correction_factors(1.0 + 1e-6):
        assert abs(1.0 - c) < 1e-6


# --------------------------------------------------------------------------- #
# 3. Legacy HI chart example (McNally Institute): 500 gpm, 3000 SSU, 150 ft
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("rpm, b_expected", [(1750, 13.92), (3550, 11.67)])
def test_legacy_chart_example(rpm, b_expected):
    b = b_parameter(
        Q_(648, "cSt"), Q_(500, "gallon/minute"), Q_(150, "ft"), Q_(rpm, "rpm")
    )
    assert b == pytest.approx(b_expected, abs=0.05)
    c_q, c_h, _c_eta = correction_factors(b)
    assert abs(c_q - 0.80) <= 0.05  # chart C_Q
    assert abs(c_h - 0.81) <= 0.05  # chart C_H (at BEP, C_H = C_Q)


# --------------------------------------------------------------------------- #
# 4. Hand values at B = 13.92
# --------------------------------------------------------------------------- #
def test_hand_values_at_b_13_92():
    c_q, c_h, c_eta = correction_factors(13.92)
    assert c_q == pytest.approx(0.778, abs=0.002)
    assert c_eta == pytest.approx(0.412, abs=0.002)
    assert c_h == pytest.approx(c_q)  # C_H at the BEP equals C_Q


@pytest.mark.parametrize("ratio", [0.6, 0.8, 1.2])
def test_head_factor_off_bep(ratio):
    c_q, _, _ = correction_factors(13.92)
    _, c_h, _ = correction_factors(13.92, ratio)
    assert c_h == pytest.approx(1.0 - (1.0 - c_q) * ratio**0.75, rel=1e-12)


# --------------------------------------------------------------------------- #
# 5. Outside the validity range
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("b", [40.0, 55.0])
def test_b_at_or_above_40_warns_but_returns(b):
    with pytest.warns(UserWarning, match="outside method validity"):
        c_q, c_h, c_eta = correction_factors(b)
    assert 0.0 < c_q < 1.0 and 0.0 < c_h < 1.0 and 0.0 < c_eta < 1.0


def test_b_below_40_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        correction_factors(39.99)


# --------------------------------------------------------------------------- #
# BEP + to_viscous
# --------------------------------------------------------------------------- #
def test_bep_of_symmetric_curve(eff_curve):
    q, h, eta = eff_curve.bep()
    assert 170.0 < q.to("m**3/h").magnitude < 190.0
    assert eta.to("percent").magnitude == pytest.approx(62.0, abs=0.5)
    assert h.to("m").magnitude == pytest.approx(47.0, abs=1.0)


def test_to_viscous_applies_factors(eff_curve, oil):
    q_bep, h_bep, _ = eff_curve.bep()
    b = b_parameter(oil.viscosity, q_bep, h_bep, Q_(1750, "rpm"))
    assert 1.0 < b < 40.0

    new = eff_curve.to_viscous(oil)
    assert new.fluid is oil
    assert new.viscosity_correction["B"] == pytest.approx(b)
    for old, nw in zip(eff_curve.points, new.points):
        ratio = float((old.capacity / q_bep).to("dimensionless").magnitude)
        c_q, c_h, c_eta = correction_factors(b, ratio)
        assert nw.capacity.to("m**3/h").magnitude == pytest.approx(
            old.capacity.to("m**3/h").magnitude * c_q, rel=1e-9
        )
        assert nw.head.to("m").magnitude == pytest.approx(
            old.head.to("m").magnitude * c_h, rel=1e-9
        )
        assert nw.efficiency.to("dimensionless").magnitude == pytest.approx(
            old.efficiency.to("dimensionless").magnitude * c_eta, rel=1e-9
        )
        expected_kw = (oil.density * nw.capacity * G * nw.head / nw.efficiency).to("kW")
        assert nw.breaking_power.to("kW").magnitude == pytest.approx(
            expected_kw.magnitude, rel=1e-9
        )


# --------------------------------------------------------------------------- #
# 6. New instance, original untouched
# --------------------------------------------------------------------------- #
def test_to_viscous_returns_new_object_and_keeps_original(eff_curve, oil, water):
    caps = [p.capacity.to("m**3/h").magnitude for p in eff_curve.points]
    heads = [p.head.to("m").magnitude for p in eff_curve.points]
    powers = [p.breaking_power.to("kW").magnitude for p in eff_curve.points]

    new = eff_curve.to_viscous(oil)

    assert new is not eff_curve
    assert new.points is not eff_curve.points
    assert eff_curve.fluid is water
    assert eff_curve.viscosity_correction is None
    assert [p.capacity.to("m**3/h").magnitude for p in eff_curve.points] == caps
    assert [p.head.to("m").magnitude for p in eff_curve.points] == heads
    assert [p.breaking_power.to("kW").magnitude for p in eff_curve.points] == powers


def test_to_viscous_warns_outside_validity(eff_curve):
    very_viscous = Fluid("Tar", density=Q_(1000, "kg/m**3"), viscosity=Q_(50000, "cSt"))
    with pytest.warns(UserWarning, match="outside method validity"):
        new = eff_curve.to_viscous(very_viscous)
    assert new.viscosity_correction["B"] >= 40.0


# --------------------------------------------------------------------------- #
# 7. B < 1 -> no change, bit-identical to the density-only path
# --------------------------------------------------------------------------- #
def test_to_viscous_below_one_equals_to_fluid(eff_curve, light):
    via_viscous = eff_curve.to_viscous(light)
    via_fluid = eff_curve.to_fluid(light)
    assert via_viscous.viscosity_correction["B"] < 1.0
    for a, b in zip(via_viscous.points, via_fluid.points):
        assert a.capacity.to("m**3/h").magnitude == b.capacity.to("m**3/h").magnitude
        assert a.head.to("m").magnitude == b.head.to("m").magnitude
        assert a.efficiency.magnitude == b.efficiency.magnitude
        assert (
            a.breaking_power.to("kW").magnitude == b.breaking_power.to("kW").magnitude
        )


def _g(value, unit):
    return Pressure(Q_(value, unit), "g")


def _b34004a_set():
    rows = []
    for q, dp_bar, kw in [
        (4.0, 33.6, 20.0),
        (6.0, 33.4, 22.0),
        (8.0, 32.7, 24.0),
        (9.8, 31.2, 25.0),
        (11.0, 29.3, 26.0),
    ]:
        rows.append(
            TestRow(
                q=Q_(q, "m**3/h"),
                p_suction=_g(1.0, "bar"),
                p_discharge=_g(1.0 + dp_bar, "bar"),
                temperature=Q_(25.0, "degC"),
                speed=Q_(10212, "rpm"),
                power=Q_(kw, "kW"),
            )
        )
    return TestPointSet(pump_tag="B-34004A", rows=tuple(rows))


def _rated(visc_cst):
    return RatedPoint(
        tag="B-34004",
        standard="API610",
        q=Q_(9.8, "m**3/h"),
        head=Q_(339.4, "m"),
        speed=Q_(10212, "rpm"),
        power=Q_(24.6, "kW"),
        density=Q_(995, "kg/m**3"),
        viscosity=Q_(visc_cst, "cSt"),
    )


def test_binding_low_viscosity_is_bit_identical():
    rated, tps = _rated(0.52), _b34004a_set()
    plain = correct_curve(rated, tps, apply_viscosity=False)
    visc = correct_curve(rated, tps, apply_viscosity=True)

    assert plain.viscous is None
    assert visc.viscous["B"] < 1.0
    assert (visc.viscous["C_Q"], visc.viscous["C_H"], visc.viscous["C_eta"]) == (
        1.0,
        1.0,
        1.0,
    )
    assert plain.before_after == visc.before_after
    for a, b in zip(plain.curve.points, visc.curve.points):
        assert a.capacity.to("m**3/h").magnitude == b.capacity.to("m**3/h").magnitude
        assert a.head.to("m").magnitude == b.head.to("m").magnitude
        assert a.efficiency.magnitude == b.efficiency.magnitude
        assert (
            a.breaking_power.to("kW").magnitude == b.breaking_power.to("kW").magnitude
        )


def test_binding_viscous_liquid_reduces_head_and_reports_factors():
    rated, tps = _rated(500.0), _b34004a_set()
    plain = correct_curve(rated, tps, apply_viscosity=False)
    visc = correct_curve(rated, tps, apply_viscosity=True)

    assert plain.viscous is None
    assert 1.0 < visc.viscous["B"] < 40.0
    assert set(visc.viscous) == {"B", "C_Q", "C_H", "C_eta"}
    assert visc.viscous["C_eta"] < 1.0
    for a, b in zip(plain.curve.points, visc.curve.points):
        assert b.head.to("m").magnitude < a.head.to("m").magnitude


# --------------------------------------------------------------------------- #
# Report sentence
# --------------------------------------------------------------------------- #
def test_viscosity_sentence_localised():
    viscous = {"B": 13.92, "C_Q": 0.778, "C_H": 0.778, "C_eta": 0.412}
    en = viscosity_sentence(LocalizationHelper("en")._, viscous)
    assert en.startswith("Viscosity correction (HI 9.6.7): B = 13.92")
    assert "C_Q = 0.778" in en and "C_η = 0.412" in en
    pt = viscosity_sentence(LocalizationHelper("pt")._, viscous)
    assert pt.startswith("Correção de viscosidade (HI 9.6.7): B = 13.92")
