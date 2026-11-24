"""Quantity-carrying signals and the binding's Quantity head/efficiency helpers (Qt-free)."""

from dataclasses import replace

import pytest

from pump import Q_, Pressure
from pumpflow.binding import row_efficiency, row_head
from pumpflow.signals import RatedPoint, TestPointSet, TestRow

G = 9.80665
RHO = Q_(1000.0, "kg/m**3")


def _g(value, unit):
    return Pressure(Q_(value, unit), "g")


def _row(p_suc, p_dis, **kw):
    base = dict(
        q=Q_(360.0, "m**3/h"),
        temperature=Q_(25.0, "degC"),
        speed=Q_(1800.0, "rpm"),
        power=Q_(200.0, "kW"),
    )
    base.update(kw)
    return TestRow(p_suction=p_suc, p_discharge=p_dis, **base)


def test_row_head_bar_matches_hand_value():
    row = _row(_g(1.8, "bar"), _g(12.53, "bar"))
    hand = (12.53 - 1.8) * 1.0e5 / (1000.0 * G)
    assert row_head(row, RHO).to("m").magnitude == pytest.approx(hand, rel=1e-9)


def test_row_head_kgf_cm2_matches_hand_value():
    row = _row(_g(1.0, "kgf/cm**2"), _g(11.0, "kgf/cm**2"))
    hand = 10.0 * 98066.5 / (1000.0 * G)  # = 100 m
    head = row_head(row, RHO)
    assert head.units == Q_(1, "m").units
    assert head.magnitude == pytest.approx(hand, rel=1e-9)
    assert head.magnitude == pytest.approx(100.0, rel=1e-9)


def test_row_head_mixed_units_equal_all_bar():
    all_bar = _row(_g(1.0, "bar"), _g(11.0, "bar"))
    mixed = _row(Pressure(Q_(1.0, "bar").to("psi"), "g"), _g(11.0, "bar"))
    assert row_head(mixed, RHO).magnitude == pytest.approx(
        row_head(all_bar, RHO).magnitude, rel=1e-9
    )


def test_row_head_default_density_is_water_at_row_temperature():
    from pump import Water

    row = _row(_g(0.0, "bar"), _g(10.0, "bar"))
    rho = Water(row.temperature).density.to("kg/m**3").magnitude
    assert row_head(row).magnitude == pytest.approx(10.0e5 / (rho * G), rel=1e-9)


def test_explicit_head_wins():
    row = _row(_g(1.0, "bar"), _g(11.0, "bar"), head=Q_(50.0, "m"))
    assert row_head(row, RHO).magnitude == pytest.approx(50.0)


def test_row_efficiency_matches_hand_value():
    row = _row(_g(0.0, "bar"), _g(10.0, "bar"))
    eff = row_efficiency(row, Q_(100.0, "m"), RHO)
    hand = 1000.0 * (360.0 / 3600.0) * G * 100.0 / 200.0e3 * 100.0
    assert eff.units == Q_(1, "percent").units
    assert eff.magnitude == pytest.approx(hand, rel=1e-9)


def test_row_efficiency_explicit_and_missing_power():
    pinned = _row(_g(0.0, "bar"), _g(10.0, "bar"), efficiency=Q_(61.0, "percent"))
    assert row_efficiency(pinned, Q_(100.0, "m"), RHO).magnitude == pytest.approx(61.0)
    no_power = _row(_g(0.0, "bar"), _g(10.0, "bar"), power=Q_(0.0, "kW"))
    assert row_efficiency(no_power, Q_(100.0, "m"), RHO) is None


def _rated(**kw):
    base = dict(
        tag="P-1",
        standard="API610",
        q=Q_(833.0, "m**3/h"),
        head=Q_(73.0, "m"),
        speed=Q_(1750.0, "rpm"),
        power=Q_(252.0, "kW"),
    )
    base.update(kw)
    return RatedPoint(**base)


def test_rated_point_validation_messages():
    assert _rated().is_valid() == (True, "")
    assert _rated(q=Q_(-1.0, "m**3/h")).is_valid() == (
        False,
        "Capacity Q must be ≥ 0 m³/h.",
    )
    assert _rated(head=Q_(0.0, "m")).is_valid() == (
        False,
        "Differential head H must be > 0 m.",
    )
    assert _rated(speed=Q_(0.0, "rpm")).is_valid() == (
        False,
        "Rated speed N must be > 0 rpm.",
    )
    assert _rated(power=Q_(0.0, "kW")).is_valid() == (
        False,
        "Rated power P must be > 0 kW.",
    )
    assert _rated(density=Q_(0.0, "kg/m**3")).is_valid() == (
        False,
        "Relative density must be > 0.",
    )
    assert _rated(tag=" ").is_valid() == (False, "A service TAG is required.")


def test_rated_density_rel():
    assert _rated(density=Q_(736.0, "kg/m**3")).density_rel == pytest.approx(0.736)
    assert _rated().density_rel == pytest.approx(1.0)


def test_has_shutoff():
    shut = _row(_g(1.0, "bar"), _g(5.0, "bar"), q=Q_(0.0, "m**3/h"))
    duty = _row(_g(1.0, "bar"), _g(5.0, "bar"))
    assert TestPointSet("A", (shut, duty, duty)).has_shutoff()
    assert not TestPointSet("A", (duty, duty, duty)).has_shutoff()


def test_has_shutoff_is_unit_aware():
    big = _row(_g(1.0, "bar"), _g(5.0, "bar"), q=Q_(0.05, "m**3/s"))  # 180 m3/h
    tiny = _row(_g(1.0, "bar"), _g(5.0, "bar"), q=Q_(1e-5, "m**3/s"))  # 0.036 m3/h
    assert not TestPointSet("A", (big,)).has_shutoff()
    assert TestPointSet("A", (tiny,)).has_shutoff()


def test_testset_validation_messages():
    good = _row(_g(1.0, "bar"), _g(5.0, "bar"))
    no_speed = replace(good, speed=Q_(0.0, "rpm"))
    assert TestPointSet("A", (good, good, no_speed)).is_valid() == (
        False,
        "Row 3: speed N is missing.",
    )
    no_dp = _row(_g(2.0, "bar"), _g(2.0, "bar"))
    assert TestPointSet("A", (good, no_dp, good)).is_valid() == (
        False,
        "Row 2: P_dis equals P_suc (no head).",
    )
