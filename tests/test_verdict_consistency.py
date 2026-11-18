"""
One verdict vocabulary across the workbench, and tolerance overrides that reach
the report (UI/UX review, 2026-11-17).

- ``ComplianceResult.verdict_text`` is the wording of every view: a NOT FULLY
  ASSESSED pump is never shown as REJECTED, and "provisional" / "tolerances
  overridden" are always said.
- Report Export's consolidated verdict keeps the same three states.
- A user override of the tolerances is written into the report data and stated
  in the report, and the summary limits are computed with the same tolerances
  as the verdict (``PerformanceChecker(tolerances=...)``).

The ``curve`` / ``water`` fixtures come from ``tests/conftest.py``.
"""

import pytest

from pump import Q_, PerformanceChecker
from pump.utilities.report import LocalizationHelper, tolerance_override_sentence

from pumpflow.binding import (
    assemble_report_data,
    check_compliance,
    criteria_for,
    fit_model,
    make_design_point,
)
from pumpflow.binding.reports import tolerance_override
from pumpflow.nodes.report_export import overall_verdict_text
from pumpflow.signals import (
    BranchBundle,
    ComplianceResult,
    CorrectedCurve,
    ParameterCheck,
    RatedPoint,
)


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


_OK = ParameterCheck("Head", 1.0, 1.0, 0.9, 1.1, 0.0, 0.03, True)
_NE = ParameterCheck("Power", 1.0, None, None, 1.04, None, 0.04, False, evaluated=False)
_BAD = ParameterCheck("Head", 1.0, 2.0, 0.9, 1.1, 1.0, 0.03, False)


def _approved(**kw):
    return ComplianceResult("A", (_OK,), True, **kw)


def _partial(**kw):
    return ComplianceResult("A", (_OK, _NE), False, not_evaluated=("Power",), **kw)


def _rejected(**kw):
    return ComplianceResult("A", (_BAD,), False, **kw)


# --------------------------------------------------------------------------- #
# verdict_text
# --------------------------------------------------------------------------- #
def test_verdict_text_three_states():
    assert _approved().verdict_text == "APPROVED ✓"
    assert _partial().verdict_text == "NOT FULLY ASSESSED ⚠"
    assert _rejected().verdict_text == "REJECTED ✗"


def test_verdict_text_says_provisional_and_overridden():
    text = _approved(unverified=("efficiency",), overridden=True).verdict_text
    assert text == "APPROVED ✓ (provisional, tolerances overridden)"
    assert (
        _rejected(overridden=True).verdict_text == "REJECTED ✗ (tolerances overridden)"
    )


# --------------------------------------------------------------------------- #
# Report Export consolidated verdict
# --------------------------------------------------------------------------- #
def test_overall_verdict_never_turns_not_fully_assessed_into_rejected():
    assert overall_verdict_text([_approved(), _partial()]) == "NOT FULLY ASSESSED ⚠"
    assert overall_verdict_text([_partial(), _rejected()]) == "REJECTED ✗"
    assert overall_verdict_text([_approved(), _approved()]) == "APPROVED ✓"
    assert overall_verdict_text([]) == "pending"


def test_overall_verdict_keeps_qualifiers_of_any_pump():
    text = overall_verdict_text([_approved(), _approved(overridden=True)])
    assert text == "APPROVED ✓ (tolerances overridden)"


# --------------------------------------------------------------------------- #
# PerformanceChecker honours the same overrides as the verdict engine
# --------------------------------------------------------------------------- #
def test_checker_limits_follow_tolerance_override(fitted):
    rated = _rated()
    tol = {"head": 0.10, "shutoff": 0.20, "power": 0.08}
    res = check_compliance(fitted, rated, tol)
    by_name = {p.name: p for p in res.parameters}
    checker = PerformanceChecker(
        make_design_point(rated, fitted.curve.fluid),
        fitted.curve,
        criteria=criteria_for(rated),
        tolerances=res.tolerances,
    )
    assert checker.minimum_head.to("m").magnitude == pytest.approx(73 * 0.90, abs=0.01)
    assert checker.maximum_head.to("m").magnitude == pytest.approx(
        by_name["Head"].maximum, abs=0.01
    )
    assert checker.maximum_head_shutoff.to("m").magnitude == pytest.approx(
        by_name["Shutoff Head"].maximum, abs=0.01
    )
    assert checker.maximum_breaking_power.to("kW").magnitude == pytest.approx(
        by_name["Power"].maximum, abs=0.01
    )
    assert checker.verdict().approved == res.overall_pass


def test_checker_without_override_is_unchanged(fitted):
    rated = _rated()
    dp = make_design_point(rated, fitted.curve.fluid)
    a = PerformanceChecker(dp, fitted.curve, criteria=criteria_for(rated))
    b = PerformanceChecker(
        dp, fitted.curve, criteria=criteria_for(rated), tolerances={}
    )
    assert a.acceptable_limits == b.acceptable_limits


# --------------------------------------------------------------------------- #
# Overrides reach the report
# --------------------------------------------------------------------------- #
def test_report_data_records_override_and_matching_limits(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated, {"head": 0.10})
    assert tolerance_override(res) == {"head": (0.10, pytest.approx(0.03))}
    data = assemble_report_data(
        rated, [BranchBundle(pump_tag="B-1A", fitted=fitted, compliance=res)]
    )
    entry = data["test_data"]["B-1A"]
    assert entry["tolerance_override"]["head"][0] == pytest.approx(0.10)
    _pred, head_min, head_max = entry["test_summary"]["Head"]
    assert head_min.to("m").magnitude == pytest.approx(73 * 0.90, abs=0.01)
    assert head_max.to("m").magnitude == pytest.approx(73 * 1.10, abs=0.01)


def test_report_data_without_override_has_no_key(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated)
    assert tolerance_override(res) is None
    data = assemble_report_data(
        rated, [BranchBundle(pump_tag="B-1A", fitted=fitted, compliance=res)]
    )
    assert "tolerance_override" not in data["test_data"]["B-1A"]


@pytest.mark.parametrize(
    "lang, intro",
    [
        ("en", "Tolerances overridden by the user"),
        ("pt", "Tolerâncias alteradas pelo usuário"),
    ],
)
def test_override_sentence_is_localised(lang, intro):
    _ = LocalizationHelper(lang)._
    text = tolerance_override_sentence(
        _, {"head": (0.05, 0.03), "efficiency": (0.02, None)}
    )
    assert text.startswith(intro)
    assert "±5.0 % (3.0 %)" in text and "−2.0 %" in text
    assert tolerance_override_sentence(_, None) == ""


def test_override_sentence_states_reason_or_its_absence():
    _ = LocalizationHelper("en")._
    override = {"head": (0.05, 0.03)}
    assert tolerance_override_sentence(_, override).endswith("Reason: not given.")
    text = tolerance_override_sentence(_, override, "purchaser letter 42")
    assert text.endswith("Reason: purchaser letter 42.")


def test_reason_reaches_report_data_only_when_overridden(fitted):
    rated = _rated()
    res = check_compliance(fitted, rated, {"head": 0.10}, reason="MoM 7")
    assert res.override_reason == "MoM 7"
    data = assemble_report_data(
        rated, [BranchBundle(pump_tag="B-1A", fitted=fitted, compliance=res)]
    )
    assert data["test_data"]["B-1A"]["tolerance_override_reason"] == "MoM 7"
    # a reason without an override is not a statement about anything
    assert check_compliance(fitted, rated, reason="MoM 7").override_reason == ""


def test_html_report_states_the_override(fitted, tmp_path):
    from pumpflow.binding import generate_html

    rated = _rated()
    res = check_compliance(fitted, rated, {"head": 0.10})
    data = assemble_report_data(
        rated, [BranchBundle(pump_tag="B-1A", fitted=fitted, compliance=res)]
    )
    html = open(
        generate_html(data, output_file=str(tmp_path / "r.html")), encoding="utf-8"
    ).read()
    assert "Tolerances overridden by the user" in html
