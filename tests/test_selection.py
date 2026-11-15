"""
Pump selection from a catalogue — UC-01 (sprint 12).

Pins :mod:`pump.catalogue`: the ``.pumpcurve.json`` round trip, the deterministic
ranking over a synthetic 3-pump catalogue, the rejection reasons, unit-mixed
duties, trim limits, and the seeded preferred-operating-region bounds.

Synthetic pumps (all 1480 rpm, D = 300 mm, d_min 270, d_max 310):
``H(Q) = Hb * (1.3 - 0.3 (Q/Qb)^2)`` and a parabolic efficiency peaking at
``Qb``; tested over 20 %-150 % of ``Qb``.

- A: Qb = 100 m3/h, Hb = 50 m, eta 78 %   (serves 100 m3/h @ 50 m as-is)
- B: Qb = 200 m3/h, Hb = 50 m, eta 82 %   (duty sits at 55 % of its BEP flow)
- C: Qb = 100 m3/h, Hb = 80 m, eta 70 %   (speed ratio 1.19, trim below d_min)
"""

from pathlib import Path

import pytest

from pump import AcceptanceCriteria, Fluid, PerformanceCurve, Q_, TestPoint
from pump.catalogue import (
    CURVE_SUFFIX,
    Catalogue,
    CatalogueEntry,
    load_entry,
    save_entry,
)

DUTY_Q = Q_(100.0, "m**3/h")
DUTY_H = Q_(50.0, "m")


def _entry(name, qb, hb, eta_max, speed=1480.0, d=300.0, d_min=270.0, d_max=310.0):
    water = Fluid("Water", density=Q_(997, "kg/m**3"))
    points = []
    for k in range(8):
        q = qb * (0.2 + k * (1.3 / 7))
        r = q / qb
        h = hb * (1.3 - 0.3 * r * r)
        eta = eta_max * (1 - ((q - qb) / (1.2 * qb)) ** 2)
        tp = TestPoint(
            fluid=water,
            capacity=Q_(q, "m**3/h"),
            speed_of_rotation=Q_(speed, "rpm"),
            _head=Q_(h, "m"),
        )
        power = (tp.compute_hydraulic_power / eta).to("kW")
        points.append(
            TestPoint(
                fluid=water,
                capacity=Q_(q, "m**3/h"),
                speed_of_rotation=Q_(speed, "rpm"),
                _head=Q_(h, "m"),
                breaking_power=power,
            )
        )
    curve = PerformanceCurve(water, points, polynomial_degree=3)
    return CatalogueEntry(
        name=name,
        curve=curve,
        speed=Q_(speed, "rpm"),
        diameter=Q_(d, "mm"),
        d_min=Q_(d_min, "mm"),
        d_max=Q_(d_max, "mm"),
    )


@pytest.fixture(scope="module")
def catalogue():
    return Catalogue(
        [
            _entry("C", 100.0, 80.0, 0.70),
            _entry("A", 100.0, 50.0, 0.78),
            _entry("B", 200.0, 50.0, 0.82),
        ]
    )


def _order(result):
    return [(c.entry.name, c.adaptation) for c in result]


def test_entries_are_sorted_by_name(catalogue):
    assert catalogue.names == ["A", "B", "C"]
    assert len(catalogue) == 3


def test_expected_pump_wins_and_ranking_is_deterministic(catalogue):
    result = catalogue.select(DUTY_Q, DUTY_H)
    assert _order(result) == [
        ("A", "as-is"),
        ("C", "speed"),
        ("B", "trim"),
        ("B", "speed"),
    ]
    best = result[0]
    assert best.in_por and best.value is None
    assert best.eta_at_duty.to("percent").magnitude == pytest.approx(78.0, abs=0.2)
    assert best.q_over_qbep == pytest.approx(1.0, abs=0.01)
    # in-POR candidates come first; the rest are out of the region
    assert [c.in_por for c in result] == [True, True, False, False]
    # repeat: identical order
    assert _order(catalogue.select(DUTY_Q, DUTY_H)) == _order(result)


def test_adapted_curves_pass_through_the_duty(catalogue):
    result = catalogue.select(DUTY_Q, DUTY_H)
    for cand in result[1:]:
        h = cand.curve.predict_head(DUTY_Q).to("m").magnitude
        assert h == pytest.approx(50.0, rel=2e-3)
    c_speed = next(c for c in result if c.adaptation == "speed" and c.name == "C")
    assert 1200 < c_speed.value.to("rpm").magnitude < 1300
    b_trim = next(c for c in result if c.adaptation == "trim")
    assert 270 <= b_trim.value.to("mm").magnitude <= 310
    assert b_trim.trim_margin == pytest.approx(
        310.0 / b_trim.value.to("mm").magnitude - 1
    )


def test_catalogue_curves_are_not_mutated(catalogue):
    before = [
        p.capacity.to("m**3/h").magnitude for p in catalogue.entries[2].curve.points
    ]
    catalogue.select(DUTY_Q, DUTY_H)
    after = [
        p.capacity.to("m**3/h").magnitude for p in catalogue.entries[2].curve.points
    ]
    assert before == after


def test_out_of_range_duty_gives_empty_list_with_reasons(catalogue):
    result = catalogue.select(Q_(5000.0, "m**3/h"), Q_(50.0, "m"))
    assert result == []
    assert len(result) == 0
    assert result.reasons
    names = {r.name for r in result.rejected}
    assert names == {"A", "B", "C"}
    assert all(r.reason for r in result.rejected)


def test_empty_catalogue_explains_itself():
    result = Catalogue().select(DUTY_Q, DUTY_H)
    assert result == [] and result.reasons


def test_non_positive_duty_raises(catalogue):
    with pytest.raises(ValueError):
        catalogue.select(Q_(0.0, "m**3/h"), DUTY_H)


def test_units_mixed_duty_gives_the_same_ranking(catalogue):
    base = catalogue.select(DUTY_Q, DUTY_H)
    mixed = catalogue.select(DUTY_Q.to("gallon/min"), DUTY_H.to("ft"))
    assert _order(mixed) == _order(base)
    for a, b in zip(base, mixed):
        assert a.eta_at_duty.to("percent").magnitude == pytest.approx(
            b.eta_at_duty.to("percent").magnitude, rel=1e-6
        )


def test_trim_below_minimum_diameter_is_rejected(catalogue):
    result = catalogue.select(DUTY_Q, DUTY_H)
    rej = [r for r in result.rejected if r.name == "C" and r.adaptation == "trim"]
    assert rej and "minimum" in rej[0].reason
    assert not any(c.name == "C" and c.adaptation == "trim" for c in result)


def test_trim_above_maximum_diameter_is_rejected(catalogue):
    # duty above A's curve: trimming would need an impeller larger than d_max
    result = catalogue.select(Q_(100.0, "m**3/h"), Q_(60.0, "m"), allow_speed=False)
    rej = [r for r in result.rejected if r.name == "A" and r.adaptation == "trim"]
    assert rej and "maximum" in rej[0].reason
    assert not any(c.name == "A" for c in result)


def test_adaptation_flags_are_respected(catalogue):
    only_trim = catalogue.select(DUTY_Q, DUTY_H, allow_speed=False)
    assert {c.adaptation for c in only_trim} <= {"as-is", "trim"}
    only_speed = catalogue.select(DUTY_Q, DUTY_H, allow_trim=False)
    assert {c.adaptation for c in only_speed} <= {"as-is", "speed"}
    neither = catalogue.select(DUTY_Q, DUTY_H, allow_speed=False, allow_trim=False)
    assert _order(neither) == [("A", "as-is")]
    assert any(r.name == "B" for r in neither.rejected)


def test_speed_range_is_respected():
    entry = _entry("A", 100.0, 50.0, 0.78)
    limited = CatalogueEntry(
        name="A",
        curve=entry.curve,
        speed=entry.speed,
        diameter=entry.diameter,
        speed_range=(Q_(1470.0, "rpm"), Q_(1490.0, "rpm")),
    )
    result = Catalogue([limited]).select(
        Q_(100.0, "m**3/h"), Q_(60.0, "m"), allow_trim=False
    )
    assert result == []
    assert any(r.adaptation == "speed" and "range" in r.reason for r in result.rejected)


def test_pumpcurve_round_trip(tmp_path):
    entry = _entry("A", 100.0, 50.0, 0.78)
    path = save_entry(entry, tmp_path / f"A{CURVE_SUFFIX}")
    assert path.exists()
    back = load_entry(path)
    assert back.name == "A"
    assert back.speed.to("rpm").magnitude == pytest.approx(1480.0)
    assert back.diameter.to("mm").magnitude == pytest.approx(300.0)
    assert back.d_min.to("mm").magnitude == pytest.approx(270.0)
    assert back.d_max.to("mm").magnitude == pytest.approx(310.0)
    assert len(back.curve) == len(entry.curve)
    assert back.has_efficiency
    for q in (60.0, 100.0, 140.0):
        qq = Q_(q, "m**3/h")
        assert back.curve.predict_head(qq).to("m").magnitude == pytest.approx(
            entry.curve.predict_head(qq).to("m").magnitude, rel=1e-6
        )
        assert back.curve.predict_efficiency(qq).to(
            "percent"
        ).magnitude == pytest.approx(
            entry.curve.predict_efficiency(qq).to("percent").magnitude, rel=1e-6
        )
    # the same selection result from the reloaded entry
    r1 = Catalogue([entry]).select(DUTY_Q, DUTY_H)
    r2 = Catalogue([back]).select(DUTY_Q, DUTY_H)
    assert _order(r1) == _order(r2)


def test_save_into_a_folder_names_the_file_after_the_pump(tmp_path):
    path = save_entry(_entry("B-1/A", 100.0, 50.0, 0.78), tmp_path)
    assert path.parent == tmp_path and path.name.endswith(CURVE_SUFFIX)


def test_from_folder_loads_files_and_reports_bad_ones(tmp_path):
    save_entry(_entry("A", 100.0, 50.0, 0.78), tmp_path)
    save_entry(_entry("B", 200.0, 50.0, 0.82), tmp_path)
    (tmp_path / f"broken{CURVE_SUFFIX}").write_text("{ not json", encoding="utf-8")
    (tmp_path / "ignored.json").write_text("{}", encoding="utf-8")
    cat = Catalogue.from_folder(tmp_path)
    assert cat.names == ["A", "B"]
    assert len(cat.load_errors) == 1 and "broken" in cat.load_errors[0]
    assert Catalogue.load_file(tmp_path / f"A{CURVE_SUFFIX}").name == "A"


def test_from_folder_missing_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Catalogue.from_folder(tmp_path / "nope")


def test_entry_without_power_is_rejected_not_crashing(tmp_path):
    entry = _entry("A", 100.0, 50.0, 0.78)
    path = save_entry(entry, tmp_path)
    import json

    doc = json.loads(path.read_text(encoding="utf-8"))
    for row in doc["points"]:
        row["power"] = None
        row.pop("efficiency", None)
    path.write_text(json.dumps(doc), encoding="utf-8")
    cat = Catalogue.from_folder(tmp_path)
    assert len(cat) == 1 and not cat.entries[0].has_efficiency
    result = cat.select(DUTY_Q, DUTY_H)
    assert result == [] and "efficiency" in result.reasons[0]


def test_por_bounds_are_seeded_unverified_for_every_edition():
    for key, _label in AcceptanceCriteria.available():
        crit = AcceptanceCriteria.load(key)
        sel = crit.selection
        assert (sel.por_min, sel.por_max) == (0.70, 1.20)
        assert sel.verified is False and sel.source
        assert "preferred operating region (pump selection)" in crit.unverified


def test_custom_por_changes_the_flag(catalogue):
    from dataclasses import replace

    from pump.acceptance import SelectionCriteria

    crit = replace(
        AcceptanceCriteria.default(),
        selection=SelectionCriteria(por_min=0.9, por_max=1.0),
    )
    result = catalogue.select(DUTY_Q, DUTY_H, criteria=crit)
    c_speed = next(c for c in result if c.name == "C" and c.adaptation == "speed")
    assert c_speed.in_por is False
    assert any("preferred operating region" in note for note in c_speed.reasons)


def test_examples_catalogue_loads_all_entries():
    folder = Path(__file__).resolve().parents[1] / "examples" / "catalogue"
    files = sorted(folder.glob(f"*{CURVE_SUFFIX}")) if folder.is_dir() else []
    if not files:
        pytest.skip("examples/catalogue not generated (run build_catalogue.py)")
    cat = Catalogue.from_folder(folder)
    assert not cat.load_errors
    assert len(cat) == len(files)
