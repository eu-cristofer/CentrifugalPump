"""tools/verdicts.py writes and compares project verdicts (toy fixtures only)."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "v1"
PROJECTS = [
    FIXTURES / "sample_project.pumpflow",
    FIXTURES / "example_1.pumpflow",
]


def _load():
    spec = importlib.util.spec_from_file_location(
        "verdicts_tool", ROOT / "tools" / "verdicts.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verdicts_tool"] = mod
    spec.loader.exec_module(mod)
    return mod


tool = _load()


def test_out_writes_one_json_per_project(tmp_path):
    assert tool.main([*map(str, PROJECTS), "--out", str(tmp_path)]) == 0
    for project in PROJECTS:
        data = json.loads((tmp_path / f"{project.stem}.json").read_text("utf-8"))
        assert data["file"] == project.name
        assert data["nodes"]
        for info in data["nodes"].values():
            assert set(info) == {"kind", "state", "status", "badge"}


def test_compare_with_itself_is_clean(tmp_path, capsys):
    tool.main([*map(str, PROJECTS), "--out", str(tmp_path)])
    assert tool.main([*map(str, PROJECTS), "--compare", str(tmp_path)]) == 0
    assert "2 project(s): same verdicts" in capsys.readouterr().out


def test_compare_detects_tampered_status(tmp_path, capsys):
    project = PROJECTS[0]
    tool.main([str(project), "--out", str(tmp_path)])
    exp_file = tmp_path / f"{project.stem}.json"
    data = json.loads(exp_file.read_text("utf-8"))
    node_id = sorted(data["nodes"])[0]
    data["nodes"][node_id]["status"] = "tampered-status"
    exp_file.write_text(json.dumps(data), encoding="utf-8")
    assert tool.main([str(project), "--compare", str(tmp_path)]) == 1
    assert f"{node_id}: status" in capsys.readouterr().out


def test_compare_missing_expected_file(tmp_path, capsys):
    assert tool.main([str(PROJECTS[0]), "--compare", str(tmp_path)]) == 1
    assert "no expected result" in capsys.readouterr().out


def test_duplicate_file_names_are_refused(tmp_path):
    assert tool.main([str(PROJECTS[0]), str(PROJECTS[0]), "--out", str(tmp_path)]) == 2
