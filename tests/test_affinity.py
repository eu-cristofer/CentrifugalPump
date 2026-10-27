"""
Affinity-law speed correction — UC-06 (evaluate speed change / VFD).

Pins :meth:`pump.PerformanceCurve.to_speed`: capacity scales with the speed ratio,
head with its square, breaking power with its cube — and a round-trip back to the
original speed reproduces the original curve to within 1e-6 (the UC-06 acceptance
criterion).

The ``curve`` fixture comes from ``tests/conftest.py``.
"""

import pytest

from pump import Q_


def test_to_speed_scales_capacity_head_power(curve):
    ratio = 3500 / 1750  # double the speed
    scaled = curve.to_speed(Q_(3500, "rpm"))
    for original, new in zip(curve.points, scaled.points):
        assert new.capacity.to("m**3/h").magnitude == pytest.approx(
            original.capacity.to("m**3/h").magnitude * ratio, rel=1e-9
        )
        assert new.head.to("m").magnitude == pytest.approx(
            original.head.to("m").magnitude * ratio**2, rel=1e-9
        )
        assert new.breaking_power.to("kW").magnitude == pytest.approx(
            original.breaking_power.to("kW").magnitude * ratio**3, rel=1e-9
        )


def test_to_speed_round_trip_is_identity(curve):
    # UC-06 acceptance: to_speed(N).to_speed(N0) restores the original curve.
    n0 = Q_(1750, "rpm")
    round_tripped = curve.to_speed(Q_(3500, "rpm")).to_speed(n0)
    for original, back in zip(curve.points, round_tripped.points):
        assert back.capacity.to("m**3/h").magnitude == pytest.approx(
            original.capacity.to("m**3/h").magnitude, rel=1e-6
        )
        assert back.head.to("m").magnitude == pytest.approx(
            original.head.to("m").magnitude, rel=1e-6
        )
        assert back.breaking_power.to("kW").magnitude == pytest.approx(
            original.breaking_power.to("kW").magnitude, rel=1e-6
        )
        assert back.speed_of_rotation.to("rpm").magnitude == pytest.approx(1750.0)


def test_to_speed_preserves_point_count(curve):
    scaled = curve.to_speed(Q_(2000, "rpm"))
    assert len(scaled) == len(curve)
