"""
Impeller trim — UC-07 (sprint 10).

Pins :meth:`pump.PerformanceCurve.to_diameter` (pure diameter affinity: Q ∝ D,
H ∝ D², P ∝ D³, η unchanged; ``UserWarning`` beyond ``max_trim``) and
:func:`pump.trim.diameter_for_duty` (affinity parabola ∩ fitted head curve).

The ``curve`` fixture comes from ``tests/conftest.py``.
"""

import warnings

import pytest

from pump import Q_
from pump.trim import diameter_for_duty

D1 = Q_(128, "mm")


def test_to_diameter_scales_capacity_head_power(curve):
    d2 = Q_(123, "mm")
    r = 123 / 128
    trimmed = curve.to_diameter(d2, D1)
    for original, new in zip(curve.points, trimmed.points):
        assert new.capacity.to("m**3/h").magnitude == pytest.approx(
            original.capacity.to("m**3/h").magnitude * r, rel=1e-9
        )
        assert new.head.to("m").magnitude == pytest.approx(
            original.head.to("m").magnitude * r**2, rel=1e-9
        )
        assert new.breaking_power.to("kW").magnitude == pytest.approx(
            original.breaking_power.to("kW").magnitude * r**3, rel=1e-9
        )
        assert new.efficiency.to("percent").magnitude == pytest.approx(
            original.efficiency.to("percent").magnitude, rel=1e-9
        )
        assert new.speed_of_rotation.to("rpm").magnitude == pytest.approx(1750.0)


def test_to_diameter_round_trip_is_identity(curve):
    d2 = Q_(122, "mm")
    back = curve.to_diameter(d2, D1).to_diameter(D1, d2)
    for original, again in zip(curve.points, back.points):
        assert again.capacity.to("m**3/h").magnitude == pytest.approx(
            original.capacity.to("m**3/h").magnitude, rel=1e-6
        )
        assert again.head.to("m").magnitude == pytest.approx(
            original.head.to("m").magnitude, rel=1e-6
        )
        assert again.breaking_power.to("kW").magnitude == pytest.approx(
            original.breaking_power.to("kW").magnitude, rel=1e-6
        )


def test_fitted_head_scales_with_diameter_squared(curve):
    r = 125 / 128
    trimmed = curve.to_diameter(Q_(125, "mm"), D1)
    for q in (200.0, 500.0, 800.0):
        h_ref = curve.predict_head(Q_(q, "m**3/h")).to("m").magnitude
        h_new = trimmed.predict_head(Q_(q * r, "m**3/h")).to("m").magnitude
        assert h_new == pytest.approx(h_ref * r**2, rel=1e-5)


def test_to_diameter_returns_new_instance_and_keeps_original(curve):
    before = [p.capacity.to("m**3/h").magnitude for p in curve.points]
    trimmed = curve.to_diameter(Q_(125, "mm"), D1)
    assert trimmed is not curve
    assert len(trimmed) == len(curve)
    assert [p.capacity.to("m**3/h").magnitude for p in curve.points] == before


def test_diameter_units_are_converted(curve):
    in_mm = curve.to_diameter(Q_(125, "mm"), D1)
    in_inch = curve.to_diameter(Q_(125 / 25.4, "inch"), Q_(128 / 25.4, "inch"))
    for a, b in zip(in_mm.points, in_inch.points):
        assert a.capacity.magnitude == pytest.approx(b.capacity.magnitude, rel=1e-9)


def test_warns_beyond_max_trim(curve):
    with pytest.warns(UserWarning, match="exceeds max_trim"):
        curve.to_diameter(Q_(140, "mm"), D1)  # +9.4 %


def test_no_warning_within_max_trim(curve):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        curve.to_diameter(Q_(125, "mm"), D1)  # -2.3 %
    assert not [w for w in caught if "max_trim" in str(w.message)]


def test_max_trim_is_configurable(curve):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        curve.to_diameter(Q_(140, "mm"), D1, max_trim=0.10)
    assert not [w for w in caught if "max_trim" in str(w.message)]
    with pytest.warns(UserWarning, match="exceeds max_trim"):
        curve.to_diameter(Q_(125, "mm"), D1, max_trim=0.01)


def test_invalid_diameters_raise(curve):
    with pytest.raises(ValueError):
        curve.to_diameter(Q_(0, "mm"), D1)
    with pytest.raises(ValueError):
        curve.to_diameter(Q_(125, "mm"), Q_(-1, "mm"))
    with pytest.raises(ValueError):
        curve.to_diameter(125, D1)


@pytest.mark.parametrize("d2_mm", [123.0, 133.0])
def test_diameter_for_duty_recovers_known_diameter(curve, d2_mm):
    d2 = Q_(d2_mm, "mm")
    trimmed = curve.to_diameter(d2, D1)
    q = Q_(600.0, "m**3/h")
    h = trimmed.predict_head(q)
    found = diameter_for_duty(curve, q, h, D1)
    assert found.to("mm").magnitude == pytest.approx(d2_mm, rel=1e-6)


def test_diameter_for_duty_on_the_curve_is_the_reference(curve):
    q = Q_(500.0, "m**3/h")
    h = curve.predict_head(q)
    found = diameter_for_duty(curve, q, h, D1)
    assert found.to("mm").magnitude == pytest.approx(128.0, rel=1e-6)


def test_diameter_for_duty_out_of_range_raises(curve):
    with pytest.raises(ValueError, match="tested range"):
        diameter_for_duty(curve, Q_(600.0, "m**3/h"), Q_(1.0, "m"), D1)
    with pytest.raises(ValueError):
        diameter_for_duty(curve, Q_(0.0, "m**3/h"), Q_(50.0, "m"), D1)
