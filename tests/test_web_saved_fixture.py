"""
A project saved by the web store opens on the desktop with the same results.

``tests/fixtures/web/saved_p9001a.pumpflow`` is written by the Vitest run
(``web/src/project/fixture.test.ts``): the P-9001A reference project opened in
the web store, one node moved by (+10, +5) and serialised.  ``Graph`` must load
it and evaluate every node to the same kind, state and status as the original.
"""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6", reason="PySide6 not installed; node registry needs Qt")

from pumpflow.engine import Graph  # noqa: E402
from pumpflow.persistence import read_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "examples" / "user" / "P-9001A_MRT_reference.pumpflow"
SAVED = ROOT / "tests" / "fixtures" / "web" / "saved_p9001a.pumpflow"


def _evaluate(doc):
    graph = Graph.from_dict(doc)
    graph.evaluate()
    return {n.node_id: (n.kind, n.state, n.status) for n in graph.nodes}


def test_web_saved_document_gives_the_same_statuses():
    reference = _evaluate(read_json(REFERENCE))
    saved = _evaluate(read_json(SAVED))
    assert saved == reference


def test_web_saved_document_moves_exactly_one_node():
    ref_nodes = read_json(REFERENCE)["nodes"]
    saved_nodes = read_json(SAVED)["nodes"]
    assert [n["id"] for n in saved_nodes] == [n["id"] for n in ref_nodes]
    moved = [
        (a["id"], b["x"] - a["x"], b["y"] - a["y"])
        for a, b in zip(ref_nodes, saved_nodes)
        if (a["x"], a["y"]) != (b["x"], b["y"])
    ]
    assert len(moved) == 1
    assert moved[0][1:] == (10, 5)


def test_web_saved_document_keeps_edges_and_settings():
    ref = read_json(REFERENCE)
    saved = read_json(SAVED)
    assert saved["edges"] == ref["edges"]
    assert [n["settings"] for n in saved["nodes"]] == [
        n["settings"] for n in ref["nodes"]
    ]
    assert saved["meta"] == ref["meta"]
