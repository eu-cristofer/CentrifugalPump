"""
Smoke / regression tests for the ``pump`` engineering library.

These are intentionally small, fast, and dependency-light (no Qt, no PySide6).
They pin the *numeric* behaviour of the core workflow so refactors stay honest:

    Fluid → TestPoint → PerformanceCurve → predict_* / to_speed → PerformanceChecker

Run from the repository root::

    pytest tests/test_pump_smoke.py -v

This file is the starter suite referenced in ``docs/RUN_AND_TEST.md``. Extend it
as the library grows (see the "next tests to add" list at the bottom).
"""

import math

import pytest

from pump import (
    Q_,
    Fluid,
    TestPoint,
    PerformanceCurve,
    PerformanceChecker,
    quantity_factory,
)

# The water / curve / design_point fixtures live in tests/conftest.py so every
# test module can share them.


# --------------------------------------------------------------------------- #
# Units foundation
# --------------------------------------------------------------------------- #
def test_quantity_factory_canonicalizes_capacity():
    q = quantity_factory(Q_(10, "liter/minute"))
    # STANDARD_UNITS canonicalizes capacity to m³/h.
    assert str(q.units) == "meter ** 3 / hour"
    assert q.to("m**3/h").magnitude == pytest.approx(0.6, rel=1e-9)


def test_quantity_factory_rejects_non_quantity():
    with pytest.raises(ValueError):
        quantity_factory(42)  # not a pint Quantity


# --------------------------------------------------------------------------- #
# Curve container & fitting
# --------------------------------------------------------------------------- #
def test_curve_length_and_sorting(curve):
    assert len(curve) == 5
    caps = [p.capacity.to("m**3/h").magnitude for p in curve]
    assert caps == sorted(caps)  # PerformanceCurve sorts by capacity


def test_predict_head_matches_data_near_rated(curve):
    pred = curve.predict_head(Q_(833, "m**3/h")).to("m").magnitude
    # degree-3 fit through the rated region: within ~2 m of the 73 m datum.
    assert pred == pytest.approx(73.0, abs=2.0)


def test_predict_shutoff_head(curve):
    pred = curve.predict_head(Q_(0, "m**3/h")).to("m").magnitude
    assert pred == pytest.approx(117.0, abs=2.0)


def test_mixed_fluid_curve_is_rejected(water):
    other = Fluid("Oil", density=Q_(850, "kg/m**3"))
    p1 = TestPoint(fluid=water, capacity=Q_(300, "m**3/h"),
                   speed_of_rotation=Q_(1750, "rpm"), _head=Q_(100, "m"))
    p2 = TestPoint(fluid=other, capacity=Q_(600, "m**3/h"),
                   speed_of_rotation=Q_(1750, "rpm"), _head=Q_(90, "m"))
    with pytest.raises(ValueError):
        PerformanceCurve(water, [p1, p2])


# --------------------------------------------------------------------------- #
# Affinity laws
# --------------------------------------------------------------------------- #
def test_to_speed_scales_by_affinity_laws(curve):
    scaled = curve.to_speed(Q_(3500, "rpm"))  # double the speed
    ratio = 3500 / 1750
    # Capacity scales linearly with speed, head with the square.
    for original, new in zip(curve.points, scaled.points):
        assert new.capacity.to("m**3/h").magnitude == pytest.approx(
            original.capacity.to("m**3/h").magnitude * ratio, rel=1e-6
        )
        assert new.head.to("m").magnitude == pytest.approx(
            original.head.to("m").magnitude * ratio ** 2, rel=1e-6
        )


# --------------------------------------------------------------------------- #
# API 610 compliance
# --------------------------------------------------------------------------- #
def test_checker_head_tolerance_band(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    # head tolerance is ±3 % of the 73 m differential head.
    assert chk.minimum_head.to("m").magnitude == pytest.approx(73 * 0.97, abs=0.05)
    assert chk.maximum_head.to("m").magnitude == pytest.approx(73 * 1.03, abs=0.05)


def test_checker_shutoff_tolerance_tier(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    # 75 < differential_head=... ; here head=73 m ≤ 75 → 10 % shut-off tolerance.
    assert chk.shutoff_tolerance == pytest.approx(0.10)


def test_report_summary_keys(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    summary = chk.report_summary
    assert {"Head", "Breaking Power", "Efficiency", "Rated Capacity"} <= set(summary)


# --------------------------------------------------------------------------- #
# Plotting (headless) — must not raise and must return a PNG stream
# --------------------------------------------------------------------------- #
def test_plot_returns_png_stream(curve):
    stream = curve.plot_performance_curve(return_io=True)
    head = stream.read(8)
    # PNG magic number.
    assert head[:4] == b"\x89PNG"


# --------------------------------------------------------------------------- #
# Next tests to add (TODO — see docs/ARCHITECTURE.md §5):
#   * to_fluid() density correction round-trip
#   * PerformanceFitter coefficient memoization (lazy properties)
#   * efficiency computation from hydraulic vs breaking power
#   * regression against examples/*.ipynb expected numbers
# --------------------------------------------------------------------------- #
