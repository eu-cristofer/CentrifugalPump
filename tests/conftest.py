"""
Shared pytest fixtures for the ``pump`` library suite.

These were originally inlined in ``test_pump_smoke.py``; hoisting them here lets
every test module reuse the same canonical water / curve / design-point objects
without re-declaring them. Matplotlib is forced to the headless ``Agg`` backend so
plotting tests never try to open a window.
"""

import matplotlib

matplotlib.use("Agg")  # headless: never open a window during tests

import pytest

from pump import (
    Q_,
    Fluid,
    DesignPoint,
    TestPoint,
    PerformanceCurve,
)


@pytest.fixture
def water():
    """Cold water at ~997 kg/m³ — the reference fluid for the suite."""
    return Fluid("Water", density=Q_(997, "kg/m**3"))


@pytest.fixture
def curve(water):
    """A small, monotonic Q×H / Q×P performance curve at 1750 rpm."""
    rows = [
        # (capacity m³/h, head m, breaking power kW)
        (0, 117, 180),
        (300, 110, 210),
        (600, 95, 240),
        (833, 73, 252),
        (1000, 55, 260),
    ]
    points = [
        TestPoint(
            fluid=water,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=Q_(1750, "rpm"),
            _head=Q_(h, "m"),
            breaking_power=Q_(p, "kW"),
        )
        for q, h, p in rows
    ]
    return PerformanceCurve(water, points, polynomial_degree=3)


@pytest.fixture
def design_point(water):
    """Rated/design point matching the curve's rated region (833 m³/h, 73 m)."""
    return DesignPoint(
        fluid=water,
        capacity=Q_(833, "m**3/h"),
        differential_head=Q_(73, "m"),
        breaking_power=Q_(252, "kW"),
        head_shutoff=Q_(117, "m"),
    )
