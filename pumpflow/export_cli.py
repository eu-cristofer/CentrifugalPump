"""
Headless report export: ``.pumpflow`` project → Word / LaTeX / PDF / HTML.

Usage::

    python -m pumpflow.export_cli PROJECT.pumpflow [--formats docx,tex,pdf,html]
        [--lang en|pt] [--out DIR] [--stem NAME] [--template template.docx]

Loads the project into the Qt-free graph engine (:class:`pumpflow.engine.Graph`),
evaluates the whole graph exactly as the GUI does, prints every node's status, and writes the report
from the project's Report Export node (cover fields, signatories and the
Markdown notes tagged "Include in report" become the cover, the "Deviations
and open points" section and the signature block). Exits with status 1 when a
node is in error, no branch is reportable, or a requested format fails.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def build_graph(project: str):
    """Load ``project`` into an evaluated :class:`pumpflow.engine.Graph` (no Qt)."""
    from .engine import Graph
    from .persistence import read_json

    graph = Graph.from_dict(read_json(project))
    graph.evaluate()
    return graph


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


def _logic_nodes(container) -> list:
    """The ``BaseNode`` logic objects of a Graph or a GraphScene."""
    return [getattr(n, "logic", n) for n in container.nodes]


def report_inputs(container):
    """``(rated, branches, settings)`` from the project's Report Export node.

    ``container`` is a :class:`~pumpflow.engine.Graph` or a ``GraphScene``.
    """
    found = [
        n for n in container.nodes if getattr(n, "logic", n).kind == "report_export"
    ]
    if not found:
        raise SystemExit("No Report Export node in this project.")
    node = found[0]
    logic = getattr(node, "logic", node)
    if hasattr(container, "gather_inputs"):
        inputs = container.gather_inputs(node)
    else:
        inputs = container._gather_inputs(node)
    rated, branches = logic._bundle(inputs)
    return rated, branches, logic.settings


def report_notes(container) -> list:
    """Settings of every Markdown Note node (those tagged ``report`` feed the report)."""
    return [lg.settings for lg in _logic_nodes(container) if lg.kind == "markdown_note"]


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
        help="comma list of docx,tex,pdf,html (default: the node's setting, else all)",
    )
    ap.add_argument(
        "--lang", default=None, help="en or pt (default: the node's setting)"
    )
    ap.add_argument(
        "--out", default=None, help="output folder (default: the node's, else .)"
    )
    ap.add_argument("--stem", default=None, help="file name without extension")
    ap.add_argument("--template", default=None, help="custom template_*.docx")
    ap.add_argument(
        "--summary",
        action="store_true",
        help="also write the API 610 test data summary (Annex M / 8th-ed. App. T) "
        "as <stem>_test_summary.{docx,tex,pdf,xlsx}",
    )
    args = ap.parse_args(argv)

    from pump.utilities.numbers import decimal, decimal_for_language

    from .engine import Graph
    from .persistence import read_json

    graph = Graph.from_dict(read_json(args.project))
    report = [n for n in graph.nodes if n.kind == "report_export"]
    language = args.lang or (report[0].settings.get("language") if report else None)
    # the whole export (charts included) uses the report language's separator
    with decimal(decimal_for_language(language)):
        graph.evaluate()
        return _export(args, graph)


def _export(args, graph) -> int:
    from .binding import REPORT_FORMATS, assemble_report_data, export_reports

    errors_in_graph = False
    print(f"Project: {args.project}")
    for lg in _logic_nodes(graph):
        print(f"  {lg.node_id:14s} {lg.kind:17s} {lg.state:8s} {lg.status}")
        errors_in_graph |= lg.state == "error"

    rated, branches, s = report_inputs(graph)
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

    data = assemble_report_data(
        rated,
        branches,
        s.get("equipment", {}),
        settings=s,
        notes=report_notes(graph),
    )
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

    if args.summary:
        from pump.utilities.report import LocalizationHelper

        from .binding import SUMMARY_FORMATS, export_test_summary, test_data_summaries

        summaries = test_data_summaries(
            rated, reportable, s, LocalizationHelper(language)._
        )
        base = stem or Path(next(iter(paths.values()), "Report")).stem
        s_paths, s_errors = export_test_summary(
            summaries,
            SUMMARY_FORMATS,
            language=language,
            out_dir=out_dir,
            stem=f"{base}_test_summary",
        )
        for fmt, path in s_paths.items():
            print(f"  wrote summary {fmt:4s} {path}")
        for fmt, msg in s_errors.items():
            print(f"  FAILED summary {fmt}: {msg}", file=sys.stderr)
        errors = {**errors, **{f"summary-{k}": v for k, v in s_errors.items()}}
    return 1 if (errors or errors_in_graph) else 0


if __name__ == "__main__":
    sys.exit(main())
