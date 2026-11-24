"""Tracked notebooks carry no image outputs.

A chart saved inside a notebook can show a tag or a vendor as pixels, which the
leak guard (a text scanner) cannot read.  Run notebooks locally to see figures;
commit them without image outputs.
"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _notebooks():
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.ipynb"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    return [ROOT / p for p in out.split("\0") if p]


def test_no_image_outputs_or_attachments():
    offenders = []
    for path in _notebooks():
        nb = json.loads(path.read_text(encoding="utf-8"))
        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("attachments"):
                offenders.append(f"{path.relative_to(ROOT)} cell {i}: attachment")
            for out in cell.get("outputs", []):
                if any(k.startswith("image/") for k in out.get("data", {})):
                    offenders.append(f"{path.relative_to(ROOT)} cell {i}: image")
    assert not offenders, offenders
