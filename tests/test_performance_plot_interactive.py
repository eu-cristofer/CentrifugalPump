"""Performance Plot: NPSH chart, interactive cursor/toolbar, and manual axis
limits that start from the limits in use."""

import os
from pathlib import Path

import pytest

PROJECT = (
    Path(__file__).resolve().parents[1]
    / "examples/user/B-34004A_MRT_reference.pumpflow"
)


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="PySide6 not installed; GUI tests skipped")
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def inputs(qapp):
    from pumpflow.export_cli import build_scene, report_inputs

    _app, scene = build_scene(str(PROJECT))
    rated, branches, _s = report_inputs(scene)
    (b,) = branches
    assert b.npsh is not None
    out = {"FittedModel": [b.fitted], "RatedPoint": [rated], "NPSHResult": [b.npsh]}
    yield out
    scene.dispose()


def test_figure_gets_npsh_chart_only_when_wired(inputs):
    from pumpflow.nodes.plotting import build_figure

    fitted, rated, npsh = (inputs[k][0] for k in inputs)
    plain = build_figure(fitted, rated=rated)
    full = build_figure(fitted, rated=rated, npsh=npsh)
    assert set(plain.pump_axes) == {"head", "power", "efficiency"}
    assert set(full.pump_axes) == {"head", "power", "efficiency", "npsh"}
    # NPSHa (2.40 m) is drawn on the NPSH chart
    labels = [l.get_label() for l in full.pump_axes["npsh"].get_lines()]
    assert any(l.startswith("NPSHa 2.40") for l in labels)
    # readout: fitted values inside the tested range, nothing outside it
    r = full.pump_readout(9.8)
    assert set(r) == {"head", "power", "efficiency", "npsh"}
    assert r["npsh"] == pytest.approx(1.08, abs=0.02)  # NPSHr at rated
    assert full.pump_readout(50.0) == {}


def test_node_status_and_png_with_npsh(inputs):
    from pumpflow.nodes.registry import make_node

    node = make_node("performance_plot")
    out = node.compute(inputs)
    assert out["image"].getvalue().startswith(b"\x89PNG")
    assert "NPSH" in node.status
    assert "npsh_ylim" not in node.settings  # optional: stored only when set


def test_dialog_toolbar_cursor_and_limits_from_auto(inputs):
    from matplotlib.backend_bases import MouseEvent
    from PySide6.QtWidgets import QCheckBox, QLabel

    from pumpflow.nodes.registry import make_node

    node = make_node("performance_plot")
    node.compute(inputs)
    dlg = node.create_dialog(None, lambda: None)
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

    assert dlg.findChildren(NavigationToolbar2QT)
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

    canvas = dlg.findChildren(FigureCanvasQTAgg)[-1]
    fig = canvas.figure
    head_ax = fig.pump_axes["head"]
    auto_lo, auto_hi = head_ax.get_ylim()

    # hover: the readout names every fitted value at the pointer's flow
    canvas.draw()
    x, y = head_ax.transData.transform((9.8, (auto_lo + auto_hi) / 2))
    canvas.callbacks.process(
        "motion_notify_event", MouseEvent("motion_notify_event", canvas, x, y)
    )
    texts = [l.text() for l in dlg.findChildren(QLabel)]
    hover = [t for t in texts if t.startswith("Q = 9.80")]
    assert hover and "H = " in hover[0] and "NPSHr = " in hover[0]

    # Untick "auto" for Head: the limits start from the calculated ones.
    autos = [c for c in dlg.findChildren(QCheckBox) if c.text() == "auto"]
    assert len(autos) == 4  # head, power, efficiency, NPSHr
    autos[0].setChecked(False)
    lo, hi = node.settings["head_ylim"]
    assert (lo, hi) == (
        pytest.approx(auto_lo, abs=1e-3),
        pytest.approx(auto_hi, abs=1e-3),
    )
    # NPSH back to auto leaves no stored key
    autos[3].setChecked(False)
    assert node.settings["npsh_ylim"]
    autos[3].setChecked(True)
    assert "npsh_ylim" not in node.settings
    dlg.close()


def test_b34004a_wires_npsh_into_plot_and_report(inputs):
    """The reference project feeds NPSH into the Performance Plot node, and the
    report's performance curve carries the NPSHr chart (taller image)."""
    import json
    import struct

    from pumpflow.binding.reports import build_report_png
    from pumpflow.export_cli import build_scene, report_inputs

    doc = json.loads(PROJECT.read_text(encoding="utf-8"))
    edge = {
        "src_node": "npsh_a",
        "src_port": "NPSHResult",
        "dst_node": "plot_a",
        "dst_port": "NPSHResult",
    }
    assert edge in doc["edges"]

    _app, scene = build_scene(str(PROJECT))
    try:
        plot = next(n.logic for n in scene.nodes if n.logic.kind == "performance_plot")
        assert plot.status.endswith("NPSH")
        rated, (b,), _s = report_inputs(scene)

        def height(buf):
            return struct.unpack(">I", buf.getvalue()[20:24])[0]

        plain = build_report_png(b.corrected, rated)
        with_npsh = build_report_png(b.corrected, rated, npsh=b.npsh)
        assert height(with_npsh) > height(plain)
    finally:
        scene.dispose()
