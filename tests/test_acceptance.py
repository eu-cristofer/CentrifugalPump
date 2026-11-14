"""
Edition-aware acceptance criteria (Sprint 5) — Qt-free.

Covers the TOML-backed :class:`pump.acceptance.AcceptanceCriteria`, its use by
:class:`pump.PerformanceChecker`, and the F-01 / F-02 fixes. The ``water``,
``curve`` and ``design_point`` fixtures come from ``tests/conftest.py``.
"""

import warnings

import pytest

import pump.acceptance as acc
from pump import (
    Q_,
    AcceptanceCriteria,
    DesignPoint,
    PerformanceChecker,
    PerformanceCurve,
    TestPoint,
)


def _curve(water, rows):
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


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def test_available_editions():
    keys = [k for k, _ in AcceptanceCriteria.available()]
    assert keys == ["api610:8", "api610:10", "api610:11", "api610:12"]


@pytest.mark.parametrize("key", [k for k, _ in AcceptanceCriteria.available()])
def test_every_edition_loads_with_sorted_bands(key):
    crit = AcceptanceCriteria.load(key)
    assert crit.key == key
    for bands in (crit.head_bands, crit.shutoff_bands):
        limits = [b[0].to("m").magnitude for b in bands]
        assert limits == sorted(limits)
        assert limits[-1] == float("inf")
        assert all(minus >= 0 and plus >= 0 for _, minus, plus in bands)
    assert crit.power_tol_plus >= 0
    assert crit.efficiency_tol_minus >= 0
    assert crit.parallel_shutoff_min_ratio >= 1.0


def test_default_is_api610_12():
    assert AcceptanceCriteria.default().key == "api610:12"


def test_unknown_key_raises_keyerror_listing_available():
    with pytest.raises(KeyError) as exc:
        AcceptanceCriteria.load("api610:99")
    assert "api610:12" in str(exc.value)


def test_unknown_client_raises_keyerror():
    with pytest.raises(KeyError):
        AcceptanceCriteria.load("api610:12", client="nope")


def test_clients_lists_n553():
    assert ("n553", "Petrobras N-553 (client overlay)") in AcceptanceCriteria.clients()


# --------------------------------------------------------------------------- #
# Default numbers == pre-S5 behaviour (tests/test_compliance.py expectations)
# --------------------------------------------------------------------------- #
def test_default_tolerances_match_historical_values():
    crit = AcceptanceCriteria.default()
    assert crit.head_tolerance(Q_(73, "m")) == (0.03, 0.03)
    assert crit.head_tolerance(Q_(900, "m")) == (0.03, 0.03)
    assert crit.power_tol_plus == pytest.approx(0.04)
    assert crit.efficiency_tol_minus == pytest.approx(0.03)
    assert crit.parallel_shutoff_min_ratio == pytest.approx(1.10)


@pytest.mark.parametrize(
    "rated_head_m, expected",
    [(50, 0.10), (73, 0.10), (75, 0.10), (100, 0.08), (300, 0.08), (400, 0.05)],
)
def test_shutoff_tiers_keyed_by_rated_head(rated_head_m, expected):
    minus, plus = AcceptanceCriteria.default().shutoff_tolerance(Q_(rated_head_m, "m"))
    assert minus == pytest.approx(expected)
    assert plus == pytest.approx(expected)


def test_tolerance_accepts_other_length_units():
    crit = AcceptanceCriteria.default()
    assert crit.shutoff_tolerance(Q_(100 / 0.3048, "ft"))[1] == pytest.approx(0.08)


def test_deviation_formula():
    assert AcceptanceCriteria.deviation(Q_(100, "m"), Q_(97, "m")) == pytest.approx(
        -0.03
    )
    assert AcceptanceCriteria.deviation(Q_(100, "kW"), Q_(104, "kW")) == pytest.approx(
        0.04
    )
    assert AcceptanceCriteria.deviation(100.0, 110.0) == pytest.approx(0.10)


def test_checker_limits_match_default_criteria(design_point, curve):
    chk = PerformanceChecker(design_point, curve)
    assert chk.criteria.key == "api610:12"
    assert chk.head_tolerance == pytest.approx(0.03)
    assert chk.shutoff_tolerance == pytest.approx(0.10)
    assert chk.breaking_power_tolerance == pytest.approx(0.04)
    assert chk.minimum_head.to("m").magnitude == pytest.approx(73 * 0.97, abs=0.05)
    assert chk.maximum_head.to("m").magnitude == pytest.approx(73 * 1.03, abs=0.05)
    assert chk.maximum_head_shutoff.to("m").magnitude == pytest.approx(
        117 * 1.10, abs=0.05
    )
    assert chk.minimum_head_shutoff.to("m").magnitude == pytest.approx(
        117 * 0.90, abs=0.05
    )
    assert chk.maximum_breaking_power.to("kW").magnitude == pytest.approx(
        252 * 1.04, abs=0.05
    )


# --------------------------------------------------------------------------- #
# Verified / unverified and overlay merge
# --------------------------------------------------------------------------- #
def test_shipped_editions_are_unverified_seeds():
    crit = AcceptanceCriteria.default()
    assert crit.verified is False
    assert crit.unverified
    assert "seed" in crit.source


def test_n553_overlay_changes_nothing_but_is_unverified():
    base = AcceptanceCriteria.load("api610:8")
    over = AcceptanceCriteria.load("api610:8", client="n553")
    assert over.client == "n553"
    assert over.client_label == "Petrobras N-553 (client overlay)"
    assert over.head_bands == base.head_bands
    assert over.shutoff_bands == base.shutoff_bands
    assert over.power_tol_plus == base.power_tol_plus
    assert over.verified is False
    assert any("N-553" in item for item in over.unverified)


_STD_TOML = """
standard = "tst"
title = "Test standard"

[editions."1"]
label = "TST 1st edition"
source = "unit test"
verified = true
power_tol_plus = 0.04
efficiency_tol_minus = 0.03
parallel_shutoff_min_ratio = 1.10
shutoff_extrapolation_q_fraction = 0.05
head_bands = [ { max_rated_head = "inf m", tol_minus = 0.03, tol_plus = 0.03 } ]
shutoff_bands = [ { max_rated_head = "inf m", tol_minus = 0.10, tol_plus = 0.10 } ]
"""


@pytest.fixture
def tmp_standards(tmp_path, monkeypatch):
    std_dir = tmp_path / "standards"
    client_dir = std_dir / "clients"
    client_dir.mkdir(parents=True)
    (std_dir / "tst.toml").write_text(_STD_TOML, encoding="utf-8")
    monkeypatch.setattr(acc, "_STD_DIR", std_dir)
    monkeypatch.setattr(acc, "_CLIENT_DIR", client_dir)
    return client_dir


def test_verified_base_without_overlay(tmp_standards):
    crit = AcceptanceCriteria.load("tst:1")
    assert crit.verified is True
    assert crit.unverified == ()


def test_overlay_replaces_only_defined_keys(tmp_standards):
    (tmp_standards / "acme.toml").write_text(
        'client = "acme"\nlabel = "Acme"\nverified = true\npower_tol_plus = 0.02\n',
        encoding="utf-8",
    )
    base = AcceptanceCriteria.load("tst:1")
    over = AcceptanceCriteria.load("tst:1", client="acme")
    assert over.power_tol_plus == pytest.approx(0.02)
    assert over.efficiency_tol_minus == base.efficiency_tol_minus
    assert over.head_bands == base.head_bands
    assert over.verified is True
    assert over.unverified == ()


def test_unverified_overlay_makes_result_unverified(tmp_standards):
    (tmp_standards / "acme.toml").write_text(
        'client = "acme"\nlabel = "Acme"\nverified = false\n', encoding="utf-8"
    )
    over = AcceptanceCriteria.load("tst:1", client="acme")
    assert over.verified is False
    assert over.unverified == ("Acme",)


def test_verified_overlay_over_unverified_base_stays_unverified():
    # Real shipped base is unverified; a verified overlay cannot make it verified,
    # and the parts it overrides drop out of the unverified list.
    base = AcceptanceCriteria.default()
    assert base.verified is False
    assert "power tolerance" in base.unverified


# --------------------------------------------------------------------------- #
# F-01: missing shut-off / power data must not crash
# --------------------------------------------------------------------------- #
def test_f01_no_shutoff_or_power_data(water, curve):
    dp = DesignPoint(
        fluid=water,
        capacity=Q_(833, "m**3/h"),
        differential_head=Q_(73, "m"),
    )
    chk = PerformanceChecker(dp, curve)
    assert chk.minimum_head_shutoff is None
    assert chk.maximum_head_shutoff is None
    assert chk.maximum_breaking_power is None
    assert set(chk.acceptable_limits) == {"Head (min)", "Head (max)"}
    # These render paths must not raise either.
    assert "Head" in chk.check_summary
    assert "Shutoff" not in chk.check_summary
    assert chk.report_summary["Breaking Power"][2] == "-"
    assert chk.test_summary_with_limits


# --------------------------------------------------------------------------- #
# F-02: check_summary is a table of the rated-point checks only
# --------------------------------------------------------------------------- #
def test_f02_check_summary_lists_rated_rows_only(design_point, curve):
    text = PerformanceChecker(design_point, curve).check_summary
    for header in ("Parameter", "Predicted", "Min", "Max", "OK"):
        assert header in text
    for row in ("Head", "Breaking Power", "Shutoff Head"):
        assert row in text
    # Old per-raw-point columns / rows are gone.
    assert "Head OK" not in text
    assert "B. Power OK" not in text
    assert "300.00" not in text  # the raw 300 m3/h test point


def test_f02_extrapolated_note_when_no_q0_point(water, design_point):
    curve = _curve(
        water, [(300, 110, 210), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
    )
    text = PerformanceChecker(design_point, curve).check_summary
    assert "extrapolated" in text


# --------------------------------------------------------------------------- #
# Shut-off extrapolation flag
# --------------------------------------------------------------------------- #
def test_shutoff_not_extrapolated_with_q0_point(design_point, curve):
    assert PerformanceChecker(design_point, curve).shutoff_extrapolated is False


def test_shutoff_extrapolated_without_low_flow_point(water, design_point):
    curve = _curve(
        water, [(300, 110, 210), (600, 95, 240), (833, 73, 252), (1000, 55, 260)]
    )
    assert PerformanceChecker(design_point, curve).shutoff_extrapolated is True


# --------------------------------------------------------------------------- #
# Parallel-operation rule: shut-off head >= 1.10 x rated head
# --------------------------------------------------------------------------- #
def test_parallel_operation_ok(design_point, curve):
    # ~117 m shut-off / 73 m rated = 1.6
    assert PerformanceChecker(design_point, curve).parallel_operation_ok() is True


def test_parallel_operation_fails_when_shutoff_too_flat(water, curve):
    dp = DesignPoint(
        fluid=water,
        capacity=Q_(833, "m**3/h"),
        differential_head=Q_(150, "m"),
        breaking_power=Q_(252, "kW"),
        head_shutoff=Q_(117, "m"),
    )
    assert PerformanceChecker(dp, curve).parallel_operation_ok() is False


# --------------------------------------------------------------------------- #
# acceptable_limits argument is deprecated and ignored
# --------------------------------------------------------------------------- #
def test_acceptable_limits_argument_warns(design_point, curve):
    with pytest.warns(DeprecationWarning, match="acceptable_limits is ignored"):
        chk = PerformanceChecker(
            design_point, curve, acceptable_limits={"Head (min)": 1.0}
        )
    assert chk.minimum_head.to("m").magnitude == pytest.approx(73 * 0.97, abs=0.05)


def test_no_warning_without_acceptable_limits(design_point, curve):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        PerformanceChecker(design_point, curve)
