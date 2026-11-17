"""
Sprint 5 — workbench binding of the acceptance engine (Qt-free).

Covers the free-text ``standard`` parser, the codec's v1 upgrade, the unified
deviation formula ``(predicted − rated) / rated`` in ``check_compliance``, the
criteria-keyed default tolerances, and that the GUI limits equal the library
``PerformanceChecker`` limits for the same rated point.

The ``curve`` / ``water`` fixtures come from ``tests/conftest.py``.
"""

import pytest

from pump import Q_, PerformanceChecker

from pumpflow.binding import (
    assemble_report_data,
    check_compliance,
    criteria_for,
    default_tolerances,
    fit_model,
    make_design_point,
)
from pumpflow.persistence import migrate
from pumpflow.settings_codec import parse_standard_text
from pumpflow.signals import BranchBundle, CorrectedCurve, RatedPoint


def _rated(**kw) -> RatedPoint:
    base = dict(
        tag="B-1",
        standard="API610 (12a ed.) / ISO 13709 + N-553",
        q=Q_(833, "m**3/h"),
        head=Q_(73, "m"),
        speed=Q_(1750, "rpm"),
        power=Q_(252, "kW"),
        head_shutoff=Q_(117, "m"),
    )
    base.update(kw)
    return RatedPoint(**base)


@pytest.fixture
def fitted(curve, water):
    corrected = CorrectedCurve(
        pump_tag="B-1A", curve=curve, fluid=water, target_speed=Q_(1750, "rpm")
    )
    return fit_model(corrected, degree=3)


# --------------------------------------------------------------------------- #
# Free-text parser
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "text, expected",
    [
        ("API610 (12a ed.) / ISO 13709 + N-553", ("api610:12", "n553")),
        ("API 610 8th + N-553C + API 682 3rd", ("api610:8", "n553")),
        ("API 610 11ª edição", ("api610:11", None)),
        ("api610 (10", ("api610:10", None)),
        ("API 610 9th", ("api610:12", None)),  # unknown edition -> default
        ("API 610 / ISO 13709", ("api610:12", None)),  # 13709 is not an edition
        ("n553 only", ("api610:12", "n553")),
        ("garbage", ("api610:12", None)),
        ("", ("api610:12", None)),
        (None, ("api610:12", None)),
    ],
)
def test_parse_standard_text(text, expected):
    assert parse_standard_text(text) == expected


def test_upgrade_v1_sets_acceptance_keys():
    v1 = {
        "nodes": [
            {
                "id": "r",
                "kind": "rated_point",
                "settings": {"q": 833.0, "standard": "API 610 8th + N-553C"},
            }
        ]
    }
    st = migrate(v1)["nodes"][0]["settings"]
    assert st["standard_key"] == "api610:8"
    assert st["client"] == "n553"
    assert migrate(migrate(v1)) == migrate(v1)


def test_upgrade_v1_without_standard_text_adds_nothing():
    v1 = {"nodes": [{"id": "r", "kind": "rated_point", "settings": {"q": 833.0}}]}
    st = migrate(v1)["nodes"][0]["settings"]
    assert "standard_key" not in st and "client" not in st


# --------------------------------------------------------------------------- #
# criteria_for / default_tolerances
# --------------------------------------------------------------------------- #
def test_criteria_for_selects_edition_and_client():
    c = criteria_for(_rated(standard_key="api610:8", client="n553"))
    assert c.key == "api610:8" and c.client == "n553"


def test_criteria_for_unknown_key_falls_back_to_default():
    c = criteria_for(_rated(standard_key="bogus:99", client=None))
    assert c.key == "api610:12"


def test_default_tolerances_from_criteria():
    tol = default_tolerances(_rated())
    eff = tol.pop("efficiency")
    assert eff is None  # efficiency is not a rated value in API 610
    assert tol == pytest.approx({"head": 0.03, "shutoff": 0.10, "power": 0.04})


def test_shutoff_tolerance_keyed_by_rated_head_not_shutoff_head():
    # rated head 73 m (<= 75 m band) even though the shut-off head is 400 m.
    tol = default_tolerances(_rated(head_shutoff=Q_(400, "m")))
    assert tol["shutoff"] == pytest.approx(0.10)
    tol = default_tolerances(_rated(head=Q_(100, "m")))
    assert tol["shutoff"] == pytest.approx(0.08)
    tol = default_tolerances(_rated(head=Q_(400, "m")))
    assert tol["shutoff"] == pytest.approx(0.05)


# --------------------------------------------------------------------------- #
# check_compliance
# --------------------------------------------------------------------------- #
def test_deviations_are_predicted_minus_rated_over_rated(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated)
    by_name = {p.name: p for p in res.parameters}

    pred_head = fitted.curve.predict_head(rated.q).to("m").magnitude
    assert by_name["Head"].deviation == pytest.approx((pred_head - 73.0) / 73.0)

    pred_power = fitted.curve.predict_breaking_power(rated.q).to("kW").magnitude
    assert by_name["Power"].deviation == pytest.approx((pred_power - 252.0) / 252.0)

    pred_so = fitted.curve.predict_head(Q_(0, "m**3/h")).to("m").magnitude
    assert by_name["Shutoff Head"].deviation == pytest.approx((pred_so - 117.0) / 117.0)


def test_result_carries_criteria_metadata(fitted):
    res = check_compliance(fitted, _rated(standard_key="api610:8", client="n553"))
    assert "API 610" in res.criteria_label and "Petrobras" in res.criteria_label
    # API 610 8th + N-553 rev E: performance tolerances checked against the text.
    assert res.unverified == ()
    assert all(p.verified is True for p in res.parameters)
    assert res.parallel_ok is None  # not a parallel-operation unit


def test_shutoff_not_extrapolated_when_curve_has_q0_point(fitted):
    res = check_compliance(fitted, _rated())
    so = next(p for p in res.parameters if p.name == "Shutoff Head")
    assert so.extrapolated is False


def test_parallel_rule_only_when_requested(fitted):
    res = check_compliance(fitted, _rated(parallel_operation=True))
    assert res.parallel_ok is True  # 117 m / 73 m = 1.6 >= 1.10
    assert res.overall_pass == all(p.passed for p in res.parameters)


def test_user_override_changes_band_and_flag(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated, {"head": 0.10})
    head = next(p for p in res.parameters if p.name == "Head")
    assert res.overridden is True
    assert head.minimum == pytest.approx(73 * 0.90)
    assert head.maximum == pytest.approx(73 * 1.10)
    assert head.tolerance == pytest.approx(0.10)
    assert check_compliance(fitted, rated).overridden is False


def test_gui_limits_equal_library_checker_limits(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated)
    by_name = {p.name: p for p in res.parameters}
    checker = PerformanceChecker(
        make_design_point(rated, fitted.curve.fluid),
        fitted.curve,
        criteria=criteria_for(rated),
    )
    assert by_name["Head"].minimum == pytest.approx(
        checker.minimum_head.to("m").magnitude, abs=0.01
    )
    assert by_name["Head"].maximum == pytest.approx(
        checker.maximum_head.to("m").magnitude, abs=0.01
    )
    assert by_name["Shutoff Head"].minimum == pytest.approx(
        checker.minimum_head_shutoff.to("m").magnitude, abs=0.01
    )
    assert by_name["Shutoff Head"].maximum == pytest.approx(
        checker.maximum_head_shutoff.to("m").magnitude, abs=0.01
    )
    assert by_name["Power"].maximum == pytest.approx(
        checker.maximum_breaking_power.to("kW").magnitude, abs=0.01
    )


# --------------------------------------------------------------------------- #
# Report data
# --------------------------------------------------------------------------- #
def test_assemble_report_data_carries_acceptance(fitted):
    rated = _rated(standard_key="api610:8", client="n553")
    data = assemble_report_data(rated, [BranchBundle(pump_tag="B-1A", fitted=fitted)])
    acc = data["acceptance"]
    assert "API 610" in acc["label"] and "Petrobras" in acc["label"]
    assert acc["verified"] is True
    # Open items outside the performance verdict are still listed for the report.
    assert acc["unverified"] == ["mechanical running test limits"]
    assert "B-1A" in data["test_data"]
