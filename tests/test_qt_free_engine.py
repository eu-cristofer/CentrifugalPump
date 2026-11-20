"""
The graph engine path must work in an interpreter without Qt (Pyodide, sprint 2).

A subprocess installs a ``sys.meta_path`` finder that makes ``PySide6``,
``shiboken6`` and ``pyqtgraph`` unimportable *before* ``pumpflow`` is imported,
then loads and evaluates the B-34004A regression project with
:class:`pumpflow.engine.Graph` and writes the HTML report.  The node states it
prints must equal those of an in-process run.  A static guard also checks that no
node module imports Qt, ``ui``, ``plotting`` or ``style`` at module level.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "user" / "B-34004A_MRT_reference.pumpflow"
NODES_DIR = ROOT / "pumpflow" / "nodes"

_MARKER = "STATES_JSON:"

_SUBPROCESS_CODE = """
import json
import sys


class _BlockQt:
    _BLOCKED = ("PySide6", "shiboken6", "pyqtgraph")

    def find_spec(self, name, path, target=None):
        for root in self._BLOCKED:
            if name == root or name.startswith(root + "."):
                raise ImportError("blocked in the Qt-free test: " + name)
        return None


sys.meta_path.insert(0, _BlockQt())

project, out_html = sys.argv[1], sys.argv[2]

from pumpflow.engine import Graph
from pumpflow.persistence import read_json

graph = Graph.from_dict(read_json(project))
graph.evaluate()
states = {n.node_id: [n.kind, n.state, n.status] for n in graph.nodes}

from pumpflow.export_cli import report_inputs, report_notes
from pumpflow.binding import assemble_report_data, generate_html

rated, branches, s = report_inputs(graph)
data = assemble_report_data(
    rated,
    branches,
    s.get("equipment", {}),
    settings=s,
    notes=report_notes(graph),
)
generate_html(data, output_file=out_html)

leaked = sorted(
    m for m in sys.modules if m.split(".")[0] in ("PySide6", "shiboken6", "pyqtgraph")
)
assert not leaked, leaked

print("STATES_JSON:" + json.dumps(states))
"""


def _in_process_states() -> dict:
    from pumpflow.engine import Graph
    from pumpflow.persistence import read_json

    graph = Graph.from_dict(read_json(str(PROJECT)))
    graph.evaluate()
    return {n.node_id: [n.kind, n.state, n.status] for n in graph.nodes}


@pytest.mark.skipif(not PROJECT.is_file(), reason="B-34004A reference project missing")
def test_engine_and_html_report_run_without_qt(tmp_path):
    env = dict(os.environ)
    env.pop("QT_QPA_PLATFORM", None)
    env["MPLBACKEND"] = "Agg"
    out_html = tmp_path / "report.html"

    proc = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_CODE, str(PROJECT), str(out_html)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-4000:]
    assert out_html.exists(), "generate_html wrote no file"

    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith(_MARKER)]
    assert lines, proc.stdout[-2000:]
    sub_states = json.loads(lines[-1][len(_MARKER) :])

    expected = json.loads(json.dumps(_in_process_states()))
    assert sub_states == expected


_FORBIDDEN_ROOTS = {"PySide6", "shiboken6", "pyqtgraph"}
_FORBIDDEN_LOCAL = {"ui", "plotting"}  # ``from . import ui`` / ``from .ui import x``
_FORBIDDEN_PARENT = {"style"}  # ``from ..style import x``
_QT_FREE_EXEMPT = {"ui.py", "plotting.py"}


def _module_level_imports(tree: ast.Module):
    """Import nodes executed at import time (module body, incl. if/try blocks)."""
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for field in ("body", "orelse", "finalbody"):
                stack.extend(getattr(node, field, []))
            for handler in getattr(node, "handlers", []):
                stack.extend(handler.body)


def _violations(path: Path) -> list:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in _module_level_imports(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_ROOTS:
                    found.append((node.lineno, f"import {alias.name}"))
            continue
        module = node.module or ""
        names = {a.name for a in node.names}
        if node.level == 0:
            if module.split(".")[0] in _FORBIDDEN_ROOTS:
                found.append((node.lineno, f"from {module} import ..."))
        elif node.level == 1:
            if module.split(".")[0] in _FORBIDDEN_LOCAL or (
                not module and names & _FORBIDDEN_LOCAL
            ):
                found.append((node.lineno, f"from .{module} import {sorted(names)}"))
        elif node.level == 2:
            if module.split(".")[0] in _FORBIDDEN_PARENT or (
                not module and names & _FORBIDDEN_PARENT
            ):
                found.append((node.lineno, f"from ..{module} import {sorted(names)}"))
    return found


_NODE_FILES = sorted(p for p in NODES_DIR.glob("*.py") if p.name not in _QT_FREE_EXEMPT)


def test_node_files_are_found():
    assert _NODE_FILES, "no pumpflow/nodes/*.py files found"


@pytest.mark.parametrize("path", _NODE_FILES, ids=lambda p: p.name)
def test_node_module_has_no_module_level_qt_import(path):
    assert _violations(path) == []
