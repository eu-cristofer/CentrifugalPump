"""
API 610 compliance bands — UC-02 (verify pump performance / FAT).

Pins the numeric behaviour of :class:`pump.PerformanceChecker`: the ±3 % head band,
the +4 % breaking-power ceiling, the tiered shut-off tolerance (per API 610 §8.3),
and the shape of ``report_summary``. These verdicts are safety-relevant — a silent
shift here could pass an unacceptable pump or fail a compliant one.

The ``curve`` / ``design_point`` fixtures come from ``tests/conftest.py``.
"""

import pytest

from pump import Q_, Fluid, DesignPoint, PerformanceChecker


# --------------------------------------------------------------------------- #
# Head tolerance band: ±3 % of rated differential head (73 m)
# --------------------------------------------------------------------------- #
def test_head_band_is_plus_minus_three_percent(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    assert chk.minimum_head.to("m").magnitude == pytest.approx(73 * 0.97, abs=0.05)
    assert chk.maximum_head.to("m").magnitude == pytest.approx(73 * 1.03, abs=0.05)


# --------------------------------------------------------------------------- #
# Breaking-power ceiling: +4 % of rated breaking power (252 kW)
# --------------------------------------------------------------------------- #
def test_breaking_power_ceiling_is_plus_four_percent(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    assert chk.maximum_breaking_power.to("kW").magnitude == pytest.approx(
        252 * 1.04, abs=0.05
    )


# --------------------------------------------------------------------------- #
# Shut-off tolerance tiers (API 610 §8.3): keyed on rated differential head
#   head ≤ 75 m   -> 10 %
#   75 < head ≤ 300 m -> 8 %
#   head > 300 m  -> 5 %
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "rated_head_m, expected_tol",
    [(50, 0.10), (73, 0.10), (100, 0.08), (300, 0.08), (400, 0.05)],
)
def test_shutoff_tolerance_tiers(rated_head_m, expected_tol):
    water = Fluid("Water", density=Q_(997, "kg/m**3"))
    dp = DesignPoint(
        fluid=water,
        capacity=Q_(833, "m**3/h"),
        differential_head=Q_(rated_head_m, "m"),
        breaking_power=Q_(252, "kW"),
        head_shutoff=Q_(rated_head_m + 40, "m"),
    )
    # A curve is required to construct the checker but does not affect the tier.
    chk = PerformanceChecker.__new__(PerformanceChecker)
    chk.design_point = dp
    assert chk._get_shutoff_tolerance() == pytest.approx(expected_tol)


def test_shutoff_band_uses_the_tier(design_point, curve):
    # head 73 m ≤ 75 -> 10 % around the 117 m shut-off head.
    chk = PerformanceChecker(design_point, curve)
    assert chk.shutoff_tolerance == pytest.approx(0.10)
    assert chk.maximum_head_shutoff.to("m").magnitude == pytest.approx(117 * 1.10, abs=0.05)
    assert chk.minimum_head_shutoff.to("m").magnitude == pytest.approx(117 * 0.90, abs=0.05)


# --------------------------------------------------------------------------- #
# report_summary — structure and rated-point values
# --------------------------------------------------------------------------- #
def test_report_summary_keys(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    summary = chk.report_summary
    assert {"Head", "Breaking Power", "Efficiency", "Rated Capacity"} <= set(summary)


def test_report_summary_predicts_near_rated(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    summary = chk.report_summary
    predicted_head = summary["Head"][0].to("m").magnitude
    assert predicted_head == pytest.approx(73.0, abs=2.0)
    assert summary["Rated Capacity"].to("m**3/h").magnitude == pytest.approx(833.0)


def test_acceptable_limits_exposes_all_bands(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    limits = chk.acceptable_limits
    assert {
        "Head (min)",
        "Head (max)",
        "Shutoff Head (min)",
        "Shutoff Head (max)",
        "Breaking Power (max)",
    } <= set(limits)
