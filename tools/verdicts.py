"""Compute, store and compare the verdicts of ``.pumpflow`` projects.

Usage::

    python tools/verdicts.py PROJECT.pumpflow... --out DIR
    python tools/verdicts.py PROJECT.pumpflow... --compare DIR

``--out`` writes one ``<stem>.json`` per project; ``--compare`` checks the
current verdicts against such files and exits 1 on any difference.  The private
data repo uses it (``check.sh``) to guard the real cases, whose expected results
never enter this repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_FIELDS = ("kind", "state", "status", "badge")


def summary(path) -> dict:
    """Evaluate a project and return its verdict summary.

    Parameters
    ----------
    path : str or Path
        A ``.pumpflow`` file.

    Returns
    -------
    dict
        ``{"file", "errors", "nodes": {node_id: {kind, state, status, badge}}}``.
    """
    from pumpflow.persistence import read_project
    from pumpflow.webapi import evaluate

    path = Path(path)
    result = evaluate(read_project(path))
    nodes = {}
    for node_id, info in result.get("nodes", {}).items():
        badge = info.get("badge")
        nodes[str(node_id)] = {
            "kind": info.get("kind"),
            "state": info.get("state"),
            "status": info.get("status"),
            "badge": list(badge) if badge is not None else None,
        }
    return {
        "file": path.name,
        "errors": list(result.get("errors", [])),
        "nodes": nodes,
    }


def compare(expected: dict, got: dict) -> list[str]:
    """List the differences between two summaries (empty when identical)."""
    name = got.get("file") or expected.get("file") or "?"
    diffs: list[str] = []
    if expected.get("errors", []) != got.get("errors", []):
        diffs.append(
            f"{name}: errors: expected {expected.get('errors', [])!r}, "
            f"got {got.get('errors', [])!r}"
        )
    exp_nodes = expected.get("nodes", {})
    got_nodes = got.get("nodes", {})
    for node_id in sorted(set(exp_nodes) | set(got_nodes)):
        if node_id not in got_nodes:
            diffs.append(f"{name}: {node_id}: node: expected present, got missing")
            continue
        if node_id not in exp_nodes:
            diffs.append(f"{name}: {node_id}: node: expected missing, got present")
            continue
        for field in _FIELDS:
            e = exp_nodes[node_id].get(field)
            g = got_nodes[node_id].get(field)
            if e != g:
                diffs.append(f"{name}: {node_id}: {field}: expected {e!r}, got {g!r}")
    return diffs


def main(argv=None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("projects", nargs="+", help=".pumpflow files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", metavar="DIR", help="write verdict JSON files here")
    group.add_argument("--compare", metavar="DIR", help="compare with files here")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.projects]
    stems = [p.stem for p in paths]
    if len(set(stems)) != len(stems):
        print("error: two projects share a file name", file=sys.stderr)
        return 2

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for path in paths:
            text = json.dumps(
                summary(path), indent=1, ensure_ascii=False, sort_keys=True
            )
            (out / f"{path.stem}.json").write_text(text + "\n", encoding="utf-8")
        print(f"{len(paths)} project(s) written to {out}")
        return 0

    exp_dir = Path(args.compare)
    problems: list[str] = []
    for path in paths:
        exp_file = exp_dir / f"{path.stem}.json"
        if not exp_file.is_file():
            problems.append(f"{path.name}: no expected result")
            continue
        expected = json.loads(exp_file.read_text(encoding="utf-8"))
        problems.extend(compare(expected, summary(path)))
    if problems:
        for line in problems:
            print(line)
        return 1
    print(f"{len(paths)} project(s): same verdicts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
