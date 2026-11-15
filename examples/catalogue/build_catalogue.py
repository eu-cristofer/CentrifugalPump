"""
Build the example pump catalogue (``*.pumpcurve.json``) from the shipped projects.

Run from the repository root::

    python examples/catalogue/build_catalogue.py [--out examples/catalogue]

Each project is loaded into an (offscreen) canvas and evaluated exactly as the GUI
does; every Curve Fit node's fitted model is exported with the project's rated
point (speed and datasheet impeller diameters) through
``pumpflow.binding.export_pumpcurve``.  Pump tags already exported by an earlier
project are skipped, so each tag yields one file.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Curated projects only: other examples/user files are the owner's working files
# (e.g. the old B-34004.pumpflow still carries sample leftover rated values).
PROJECTS = [
    "examples/sample_project.pumpflow",
    "examples/user/B-34004A_MRT_reference.pumpflow",
] + [
    str(p.relative_to(ROOT))
    for p in sorted((ROOT / "pumpflow" / "examples").glob("*.pumpflow"))
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    from pumpflow.binding import export_pumpcurve
    from pumpflow.export_cli import build_scene

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    seen = set()
    for rel in PROJECTS:
        path = ROOT / rel
        if not path.exists():
            print(f"skip (missing): {rel}")
            continue
        _app, scene = build_scene(str(path))
        rated = None
        for item in scene.nodes:
            if item.logic.kind == "rated_point":
                rated = item.logic.outputs_cache.get("RatedPoint")
                break
        if rated is None:
            print(f"skip (no rated point): {rel}")
            continue
        for item in scene.nodes:
            if item.logic.kind != "curve_fit":
                continue
            fitted = item.logic.outputs_cache.get("FittedModel")
            if fitted is None:
                continue
            tag = str(fitted.pump_tag)
            if tag in seen:
                print(f"skip (duplicate tag {tag}): {rel}")
                continue
            seen.add(tag)
            safe = re.sub(r"[^\w.\-]+", "_", tag).strip("_")
            target = out_dir / f"{safe}.pumpcurve.json"
            written = export_pumpcurve(fitted, rated, target)
            print(f"wrote {written}  (from {rel})")
    if not seen:
        print("ERROR: no fitted curve found in any project.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
