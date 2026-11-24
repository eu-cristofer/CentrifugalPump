"""
Headless graph engine (``pumpflow.engine``): same results as the canvas scene.

``Graph`` must evaluate every v1 fixture to the statuses pinned in
``tests/fixtures/v1/expected.json``, serialise to the same document as
``GraphScene.to_dict``, follow the canvas wiring rules, and let the export CLI
run without a ``QApplication``.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="PySide6 not installed; node registry needs Qt")

from pumpflow.engine import Edge, Graph, evaluate_in_order, topo_order  # noqa: E402
from pumpflow.nodes import registry  # noqa: E402
from pumpflow.nodes.base import BaseNode, PortSpec  # noqa: E402
from pumpflow.persistence import read_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "v1"
FILES = sorted(FIXTURES.glob("*.pumpflow"))
P9001A = ROOT / "examples" / "user" / "P-9001A_MRT_reference.pumpflow"


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def expected():
    return json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def _summary(graph):
    out = {}
    for lg in graph.nodes:
        entry = [lg.kind, lg.state, lg.status]
        res = lg.outputs_cache.get("ComplianceResult")
        if res is not None:
            entry.append(
                [
                    [
                        p.name,
                        repr(p.predicted),
                        repr(p.minimum),
                        repr(p.maximum),
                        p.passed,
                    ]
                    for p in res.parameters
                ]
            )
        out[lg.node_id] = entry
    return out


def _assert_same_results(got, want, where=""):
    """Exact on structure, strings and booleans; numeric strings to 1e-9 relative."""
    if isinstance(want, dict):
        assert isinstance(got, dict) and set(got) == set(want), where
        for k in want:
            _assert_same_results(got[k], want[k], f"{where}/{k}")
    elif isinstance(want, list):
        assert isinstance(got, list) and len(got) == len(want), where
        for i, (g, w) in enumerate(zip(got, want)):
            _assert_same_results(g, w, f"{where}[{i}]")
    elif isinstance(want, str) and isinstance(got, str) and want != got:
        try:
            gv, wv = float(got), float(want)
        except ValueError:
            raise AssertionError(f"{where}: {got!r} != {want!r}")
        assert gv == pytest.approx(wv, rel=1e-9, abs=1e-12), where
    else:
        assert got == want, f"{where}: {got!r} != {want!r}"


# ---------------------------------------------------------------- stub nodes
class _Src(BaseNode):
    kind = "t_src"
    outputs = [PortSpec("o", "x")]

    def compute(self, inputs):
        return {"o": self.node_id}


class _Sink(BaseNode):
    kind = "t_sink"
    inputs = [PortSpec("i", "x")]
    outputs = [PortSpec("o", "x")]

    def compute(self, inputs):
        return {"o": len(inputs["i"])}


class _Wild(BaseNode):
    kind = "t_wild"
    inputs = [PortSpec("i", "*", multi=True)]
    outputs = [PortSpec("o", "*")]

    def compute(self, inputs):
        return {"o": list(inputs["i"])}


class _Typed(BaseNode):
    kind = "t_typed"
    inputs = [PortSpec("i", "y")]


class _Boom(BaseNode):
    kind = "t_boom"
    inputs = [PortSpec("i", "*", multi=True)]
    outputs = [PortSpec("o", "*")]

    def compute(self, inputs):
        raise RuntimeError("boom")


@pytest.fixture
def stubs(monkeypatch):
    for cls in (_Src, _Sink, _Wild, _Typed, _Boom):
        monkeypatch.setitem(registry._BY_KIND, cls.kind, cls)


# ------------------------------------------------------------ pure functions
def test_topo_order_is_stable_and_appends_cycle_leftovers():
    assert topo_order(["a", "b", "c"], [("c", "a")]) == ["b", "c", "a"]
    assert topo_order(["a", "b", "c"], []) == ["a", "b", "c"]
    assert topo_order(["a", "b", "c"], [("a", "b"), ("b", "a")]) == ["c", "a", "b"]


def test_evaluate_in_order_captures_errors_and_calls_after():
    class N:
        def __init__(self, fail):
            self.fail, self.error, self.ran = fail, "", False

        def run(self, inputs):
            self.ran = True
            if self.fail:
                raise ValueError("bad input")

        def set_error(self, message):
            self.error = message

    a, b = N(True), N(False)
    seen = []
    evaluate_in_order([a, b], lambda n: {}, after=seen.append)
    assert a.error == "bad input" and a.ran
    assert b.error == "" and b.ran
    assert seen == [a, b]


# ------------------------------------------------------------------- fixtures
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_graph_matches_pinned_fixture_results(expected, path):
    graph = Graph.from_dict(read_json(path))
    graph.evaluate()
    _assert_same_results(_summary(graph), expected[path.name], path.name)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_graph_to_dict_equals_scene_to_dict(qapp, path):
    from pumpflow.canvas.scene import GraphScene

    doc = read_json(path)
    graph = Graph.from_dict(doc)
    graph.evaluate()
    scene = GraphScene(registry.make_node)
    try:
        scene.load_dict(doc)
        assert graph.to_dict() == scene.to_dict()
    finally:
        scene.dispose()
    assert "view" not in graph.to_dict()
    assert graph.to_dict(view={"zoom": 1.0})["view"] == {"zoom": 1.0}


# --------------------------------------------------------------------- wiring
def test_cycle_still_evaluates_without_exception(stubs):
    g = Graph()
    a = g.add_node("t_wild", node_id="a")
    b = g.add_node("t_wild", node_id="b")
    assert g.connect("a", "o", "b", "i") is not None
    assert g.connect("b", "o", "a", "i") is not None
    assert g.topo_order() == [a, b]
    g.evaluate()  # must not raise
    assert a.state != "error" and b.state != "error"


def test_node_exception_becomes_node_error(stubs):
    g = Graph()
    n = g.add_node("t_boom", node_id="b1")
    g.evaluate()
    assert n.state == "error" and n.status == "boom"


def test_connect_unknown_port_or_node_raises(stubs):
    g = Graph()
    g.add_node("t_src", node_id="s")
    g.add_node("t_sink", node_id="k")
    with pytest.raises(ValueError):
        g.connect("s", "nope", "k", "i")
    with pytest.raises(ValueError):
        g.connect("s", "o", "k", "nope")
    with pytest.raises(ValueError):
        g.connect("s", "o", "missing", "i")
    with pytest.raises(ValueError):
        g.connect("k", "i", "s", "o")  # wrong direction: i is not an output


def test_connect_rejects_type_mismatch_but_allows_wildcard(stubs):
    g = Graph()
    g.add_node("t_src", node_id="s")
    g.add_node("t_typed", node_id="t")
    g.add_node("t_wild", node_id="w")
    with pytest.raises(ValueError):
        g.connect("s", "o", "t", "i")
    assert g.connect("s", "o", "w", "i") == Edge("s", "o", "w", "i")


def test_connect_duplicate_and_single_input_return_none(stubs):
    g = Graph()
    g.add_node("t_src", node_id="s1")
    g.add_node("t_src", node_id="s2")
    g.add_node("t_sink", node_id="k")
    assert g.connect("s1", "o", "k", "i") is not None
    assert g.connect("s1", "o", "k", "i") is None  # duplicate
    assert g.connect("s2", "o", "k", "i") is None  # single input already wired
    assert len(g.edges) == 1


def test_gather_inputs_keeps_connection_order(stubs):
    g = Graph()
    g.add_node("t_src", node_id="s1")
    g.add_node("t_src", node_id="s2")
    w = g.add_node("t_wild", node_id="w")
    g.connect("s2", "o", "w", "i")
    g.connect("s1", "o", "w", "i")
    g.evaluate()
    assert w.outputs_cache["o"] == ["s2", "s1"]
    assert g.gather_inputs(w) == {"i": ["s2", "s1"]}


def test_remove_node_and_disconnect(stubs):
    g = Graph()
    g.add_node("t_src", node_id="s")
    g.add_node("t_wild", node_id="w", pos=(3, 4))
    g.connect("s", "o", "w", "i")
    g.disconnect("s", "o", "w", "i")
    assert g.edges == []
    g.connect("s", "o", "w", "i")
    g.remove_node("w")
    assert g.edges == [] and g.node_by_id("w") is None
    assert [n.node_id for n in g.nodes] == ["s"]
    assert "w" not in g.positions


def test_generated_ids_follow_scene_scheme(stubs):
    g = Graph()
    assert g.add_node("t_src").node_id == "t_src-1"
    assert g.add_node("t_wild").node_id == "t_wild-2"


# ------------------------------------------------------------------ export CLI
@pytest.mark.skipif(not P9001A.exists(), reason="P-9001A reference not present")
def test_export_cli_graph_runs_without_qapplication():
    code = (
        "import sys\n"
        "from pumpflow.export_cli import build_graph\n"
        "g = build_graph(sys.argv[1])\n"
        "assert any(n.kind == 'report_export' for n in g.nodes)\n"
        "from PySide6.QtWidgets import QApplication\n"
        "assert QApplication.instance() is None\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "QT_QPA_PLATFORM"}
    proc = subprocess.run(
        [sys.executable, "-c", code, str(P9001A)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


@pytest.mark.skipif(not P9001A.exists(), reason="P-9001A reference not present")
def test_report_inputs_accept_a_graph():
    from pumpflow.export_cli import build_graph, report_inputs, report_notes

    graph = build_graph(str(P9001A))
    rated, branches, settings = report_inputs(graph)
    assert rated is not None and branches
    assert isinstance(settings, dict)
    assert isinstance(report_notes(graph), list)
