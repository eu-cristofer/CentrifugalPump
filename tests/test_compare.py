"""
Pump comparison (UC-08) — Qt-free tests for ``pump.compare`` and
``pumpflow.binding.comparison_for``.
"""

from types import SimpleNamespace

import pytest

from pump import (
    Q_,
    PerformanceCurve,
    TestPoint,
    ComparisonTable,
    compare_curves,
    plot_comparison,
)
from pumpflow.binding import comparison_for

ROWS = [
    # (capacity m³/h, head m, breaking power kW)
    (0, 117, 180),
    (300, 110, 210),
    (600, 95, 240),
    (833, 73, 252),
    (1000, 55, 260),
]


def _curve(water, head_scale=1.0):
    points = [
        TestPoint(
            fluid=water,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=Q_(1750, "rpm"),
            _head=Q_(h * head_scale, "m"),
            breaking_power=Q_(p, "kW"),
        )
        for q, h, p in ROWS
    ]
    return PerformanceCurve(water, points, polynomial_degree=3)


@pytest.fixture
def curves(water):
    return {"A": _curve(water), "B": _curve(water, 1.05)}


def test_compare_curves_deltas(curves):
    table = compare_curves(curves, [Q_(833, "m**3/h")])
    assert isinstance(table, ComparisonTable)
    assert table.tags == ("A", "B")
    assert len(table.rows) == 1
    row = table.rows[0]
    assert set(row.values) == {"A", "B"}
    assert set(row.deltas) == {"B"}  # the reference is omitted
    assert row.deltas["B"]["head"] == pytest.approx(0.05, rel=1e-9)
    assert row.deltas["B"]["power"] == pytest.approx(0.0, abs=1e-9)
    assert row.values["A"]["head"].to("m").magnitude == pytest.approx(73, rel=0.05)


def test_compare_curves_requires_two(curves):
    with pytest.raises(ValueError):
        compare_curves({"A": curves["A"]}, [Q_(833, "m**3/h")])
    with pytest.raises(ValueError):
        compare_curves({}, [Q_(833, "m**3/h")])


def test_plot_comparison_returns_png(curves):
    png = plot_comparison(curves, rated_q=Q_(833, "m**3/h"))
    assert png.read(4) == b"\x89PNG"
    png2 = plot_comparison(curves)
    assert png2.getvalue().startswith(b"\x89PNG")


def test_as_text_contains_tags(curves):
    text = compare_curves(curves, [Q_(833, "m**3/h")]).as_text()
    assert "A" in text and "B" in text
    assert "+5.00" in text


def test_comparison_for_needs_two_fitted(curves):
    rated = SimpleNamespace(q=Q_(833, "m**3/h"))
    one = [SimpleNamespace(pump_tag="A", fitted=SimpleNamespace(curve=curves["A"]))]
    assert comparison_for(one, rated) is None
    blank = SimpleNamespace(pump_tag="B", fitted=None)
    assert comparison_for(one + [blank], rated) is None


def test_comparison_for_two_fitted(curves):
    rated = SimpleNamespace(q=Q_(833, "m**3/h"))
    bundles = [
        SimpleNamespace(pump_tag=tag, fitted=SimpleNamespace(curve=c))
        for tag, c in curves.items()
    ]
    result = comparison_for(bundles, rated)
    assert result is not None
    assert result["table"].tags == ("A", "B")
    assert result["plot"].getvalue().startswith(b"\x89PNG")
    assert len(result["at"]) == 1
