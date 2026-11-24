"""Qt (offscreen) tests: Pump Selection node + dialog (sprint 12 / UC-01)."""

import os

import pytest

from pump import Fluid, PerformanceCurve, Q_, TestPoint


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _entry(name, qb, hb, eta_max):
    from pump.catalogue import CatalogueEntry

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
            speed_of_rotation=Q_(1480, "rpm"),
            _head=Q_(h, "m"),
        )
        power = (tp.compute_hydraulic_power / eta).to("kW")
        points.append(
            TestPoint(
                fluid=water,
                capacity=Q_(q, "m**3/h"),
                speed_of_rotation=Q_(1480, "rpm"),
                _head=Q_(h, "m"),
                breaking_power=power,
            )
        )
    return CatalogueEntry(
        name=name,
        curve=PerformanceCurve(water, points, polynomial_degree=3),
        speed=Q_(1480, "rpm"),
        diameter=Q_(300, "mm"),
        d_min=Q_(270, "mm"),
        d_max=Q_(310, "mm"),
    )


@pytest.fixture
def folder(tmp_path):
    from pump.catalogue import save_entry

    for e in (
        _entry("C", 100.0, 80.0, 0.70),
        _entry("A", 100.0, 50.0, 0.78),
        _entry("B", 200.0, 50.0, 0.82),
    ):
        save_entry(e, tmp_path)
    return tmp_path


def _node(folder=""):
    from pumpflow.nodes.registry import make_node

    node = make_node("selection")
    node.settings.update(
        {
            "folder": str(folder),
            "duty_q": 100.0,
            "duty_q_unit": "m³/h",
            "duty_h": 50.0,
            "duty_h_unit": "m",
        }
    )
    return node


def test_registered_kind(qapp):
    from pumpflow.nodes.registry import NODE_KINDS

    assert any(k[0] == "selection" for k in NODE_KINDS)


def test_default_instance_evaluates_without_a_catalogue(qapp):
    from pumpflow.nodes.registry import make_node

    node = make_node("selection")
    assert node.compute({}) == {}
    assert node.state == "idle" and node.status == "no catalogue"


def test_nonexistent_folder_is_no_catalogue(qapp, tmp_path):
    node = _node(tmp_path / "does-not-exist")
    assert node.compute({}) == {}
    assert node.state == "idle" and node.status == "no catalogue"


def test_empty_folder_is_idle(qapp, tmp_path):
    node = _node(tmp_path)
    assert node.compute({}) == {}
    assert node.state == "idle" and "no catalogue" in node.status


def test_ranks_a_catalogue_and_emits_the_top_rated_point(qapp, folder):
    node = _node(folder)
    out = node.compute({})
    assert node.state == "ok", node.status
    result = node._result
    assert [(c.entry.name, c.adaptation) for c in result][0] == ("A", "as-is")
    rated = out["RatedPoint"]
    assert rated.q.to("m**3/h").magnitude == pytest.approx(100.0)
    assert rated.head.to("m").magnitude == pytest.approx(50.0)
    assert rated.speed.to("rpm").magnitude == pytest.approx(1480.0)
    assert rated.power.to("kW").magnitude > 0
    assert rated.efficiency.to("percent").magnitude == pytest.approx(78.0, abs=0.3)
    assert rated.impeller_diameter.to("mm").magnitude == pytest.approx(300.0)
    ok, msg = rated.is_valid()
    assert ok, msg
    assert "A" in node.status and "candidate" in node.status


def test_choice_selects_another_row(qapp, folder):
    node = _node(folder)
    node.settings["choice"] = 1  # C @ speed
    out = node.compute({})
    assert node.state == "ok"
    assert 1200 < out["RatedPoint"].speed.to("rpm").magnitude < 1300
    node.settings["choice"] = 99  # clamped to the last row
    node.compute({})
    assert node.state == "ok"


def test_gpm_ft_duty_gives_the_same_result(qapp, folder):
    node = _node(folder)
    node.compute({})
    base = [(c.entry.name, c.adaptation) for c in node._result]
    node.settings.update(
        {
            "duty_q": Q_(100.0, "m**3/h").to("gallon/min").magnitude,
            "duty_q_unit": "US GPM",
            "duty_h": Q_(50.0, "m").to("ft").magnitude,
            "duty_h_unit": "ft",
        }
    )
    node.compute({})
    assert [(c.entry.name, c.adaptation) for c in node._result] == base


def test_no_pump_fits_is_invalid(qapp, folder):
    node = _node(folder)
    node.settings["duty_q"] = 5000.0
    assert node.compute({}) == {}
    assert node.state == "invalid" and "no pump fits" in node.status
    assert node._result is not None and node._result.reasons


def test_non_positive_duty_is_invalid(qapp, folder):
    node = _node(folder)
    node.settings["duty_h"] = 0.0
    assert node.compute({}) == {}
    assert node.state == "invalid"


def test_settings_codec_round_trip(qapp):
    from pumpflow.settings_codec import decode, encode

    rt = {
        "folder": "x",
        "duty_q": 100.0,
        "duty_q_unit": "US GPM",
        "duty_h": 50.0,
        "duty_h_unit": "ft",
        "allow_speed": True,
        "allow_trim": False,
        "choice": 2,
    }
    v2 = encode("selection", rt)
    assert v2["duty_q"]["value"] == 100.0
    assert "duty_q_unit" not in v2 and v2["folder"] == "x" and v2["choice"] == 2
    assert decode("selection", v2) == rt
    assert encode("selection", decode("selection", v2)) == v2


def test_export_pumpcurve_binding_round_trip(qapp, tmp_path):
    from pumpflow.binding import export_pumpcurve, fit_model
    from pumpflow.nodes.registry import make_node
    from pumpflow.signals import CorrectedCurve
    from pump.catalogue import load_entry

    entry = _entry("B-9", 100.0, 50.0, 0.78)
    corrected = CorrectedCurve(
        pump_tag="B-9",
        curve=entry.curve,
        fluid=entry.curve.fluid,
        target_speed=Q_(1480, "rpm"),
    )
    fitted = fit_model(corrected, degree=3)
    rn = make_node("rated_point")
    rn.settings.update(
        {"d_imp": 300.0, "d_imp_unit": "mm", "d_max": 310.0, "d_max_unit": "mm"}
    )
    rated = rn.compute({})["RatedPoint"]
    out = export_pumpcurve(fitted, rated, tmp_path)
    back = load_entry(out)
    assert back.name == "B-9"
    assert back.speed.to("rpm").magnitude == pytest.approx(1480.0)
    assert back.diameter.to("mm").magnitude == pytest.approx(300.0)
    assert back.d_max.to("mm").magnitude == pytest.approx(310.0)
    assert back.d_min is None
    assert back.has_efficiency


def test_selection_dialog_opens(qapp, folder):
    from PySide6.QtWidgets import QTableWidget

    from pumpflow.nodes.registry import make_node

    node = make_node("selection")
    dlg = node.create_dialog(None, lambda: None)
    assert dlg is not None
    dlg.close()

    node = _node(folder)
    node.compute({})
    calls = []
    dlg = node.create_dialog(None, lambda: (calls.append(1), node.compute({})))
    table = dlg.findChild(QTableWidget)
    assert table is not None and table.rowCount() == len(node._result) > 0
    dlg.close()
