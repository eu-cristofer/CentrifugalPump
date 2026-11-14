"""
Headless report export: ``.pumpflow`` project → Word / LaTeX / PDF.

Usage::

    python -m pumpflow.export_cli PROJECT.pumpflow [--formats docx,tex,pdf]
        [--lang en|pt] [--out DIR] [--stem NAME] [--template template.docx]

Loads the project into a real (offscreen) canvas, evaluates the whole graph
exactly as the GUI does, prints every node's status, and writes the report
from the project's Report Export node. Exits with status 1 when a node is in
error, no branch is reportable, or a requested format fails.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def build_scene(project: str):
    """Load ``project`` into an evaluated :class:`GraphScene` (offscreen Qt)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from .canvas.scene import GraphScene
    from .nodes.registry import make_node
    from .persistence import read_json

    scene = GraphScene(make_node)
    scene.load_dict(read_json(project))  # load_dict() also evaluates the graph
    return app, scene


def report_inputs(scene):
    """``(rated, branches, settings)`` from the project's Report Export node."""
    items = [n for n in scene.nodes if n.logic.kind == "report_export"]
    if not items:
        raise SystemExit("No Report Export node in this project.")
    item = items[0]
    rated, branches = item.logic._bundle(scene._gather_inputs(item))
    return rated, branches, item.logic.settings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m pumpflow.export_cli",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("project", help="path to a .pumpflow project")
    ap.add_argument(
        "--formats",
        default=None,
        help="comma list of docx,tex,pdf (default: the node's setting, else all)",
    )
    ap.add_argument(
        "--lang", default=None, help="en or pt (default: the node's setting)"
    )
    ap.add_argument(
        "--out", default=None, help="output folder (default: the node's, else .)"
    )
    ap.add_argument("--stem", default=None, help="file name without extension")
    ap.add_argument("--template", default=None, help="custom template_*.docx")
    args = ap.parse_args(argv)

    from .binding import REPORT_FORMATS, assemble_report_data, export_reports

    _app, scene = build_scene(args.project)

    errors_in_graph = False
    print(f"Project: {args.project}")
    for item in scene.nodes:
        lg = item.logic
        print(f"  {lg.node_id:14s} {lg.kind:17s} {lg.state:8s} {lg.status}")
        errors_in_graph |= lg.state == "error"

    rated, branches, s = report_inputs(scene)
    if rated is None:
        print("ERROR: Report Export has no Rated Point.", file=sys.stderr)
        return 1
    reportable = [b for b in branches if b.fitted is not None]
    if not reportable:
        print("ERROR: no branch has a fitted curve to report.", file=sys.stderr)
        return 1
    skipped = [b.pump_tag for b in branches if b.fitted is None]
    if skipped:
        print(f"  (not reported, incomplete: {', '.join(skipped)})")

    formats = (
        args.formats.split(",")
        if args.formats
        else s.get("formats") or list(REPORT_FORMATS)
    )
    language = args.lang or s.get("language") or "en"
    out_dir = args.out or s.get("out_dir") or "."
    template = args.template or s.get("template_path") or None
    stem = args.stem or s.get("filename") or None
    if stem:
        stem = Path(stem).stem

    data = assemble_report_data(rated, branches, s.get("equipment", {}))
    paths, errors = export_reports(
        data,
        [f.strip() for f in formats if f.strip()],
        language=language,
        template_path=template,
        out_dir=out_dir,
        stem=stem,
    )
    for fmt, path in paths.items():
        print(f"  wrote {fmt:4s} {path}")
    for fmt, msg in errors.items():
        print(f"  FAILED {fmt}: {msg}", file=sys.stderr)
    return 1 if (errors or errors_in_graph) else 0


if __name__ == "__main__":
    sys.exit(main())
