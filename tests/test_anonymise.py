"""Tests for tools/anonymise.py: names change, numbers never do.

Uses toy words only.  The project-file test builds its map dynamically from the
tags found inside the fixture, so no real tag is written in this file.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "anonymise.py"
FIXTURE = ROOT / "tests" / "fixtures" / "v1" / "sample_project.pumpflow"


def _load():
    spec = importlib.util.spec_from_file_location("anonymise_tool", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["anonymise_tool"] = mod
    spec.loader.exec_module(mod)
    return mod


anon = _load()


def _write_map(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "map.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _mapping(replace: dict, ignore_case=()):
    return anon.Mapping(list(replace.items()), set(ignore_case))


def _numbers(obj) -> list:
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [obj]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in _numbers(v)]
    if isinstance(obj, list):
        return [n for v in obj for n in _numbers(v)]
    return []


def _setting(doc: dict, kind: str, key: str) -> str:
    for node in doc["nodes"]:
        if node.get("kind") == kind:
            return node["settings"][key]
    raise AssertionError(f"no {kind} node in the fixture")


def test_project_file_names_change_numbers_do_not(tmp_path):
    from pumpflow import webapi
    from pumpflow.persistence import migrate

    before = FIXTURE.read_text(encoding="utf-8")
    doc = json.loads(before)
    tag = _setting(doc, "rated_point", "tag")
    pump_tag = _setting(doc, "test_points", "pump_tag")
    replace = {tag: "P-0001", pump_tag: "P-0001A"}
    target = tmp_path / "copy.pumpflow"
    target.write_text(before, encoding="utf-8")

    map_path = _write_map(tmp_path, {"replace": replace})
    assert anon.main(["--map", str(map_path), str(target)]) == 0

    after = target.read_text(encoding="utf-8")
    new_doc = json.loads(after)  # still valid JSON
    assert _numbers(new_doc) == _numbers(doc)
    assert tag not in after
    assert pump_tag not in after
    assert "P-0001A" in after

    mapping = anon.load_map(map_path)

    def states(d, rewrite=False):
        out = {}
        for nid, n in webapi.evaluate(migrate(d))["nodes"].items():
            status = n["status"]
            if rewrite:  # status lines quote the tag; the rest must not move
                status = anon.anonymise_text(status, mapping)[0]
            out[nid] = (n["state"], status, n["badge"])
        return out

    assert states(new_doc) == states(json.loads(before), rewrite=True)


@pytest.mark.parametrize("key", ["1234", "12-34", "1.5", " 7_8 ", "-"])
def test_numeric_only_key_is_refused(tmp_path, key):
    path = _write_map(tmp_path, {"replace": {key: "ACME"}})
    with pytest.raises(ValueError):
        anon.load_map(path)
    target = tmp_path / "a.txt"
    target.write_text("x 1234 y", encoding="utf-8")
    assert anon.main(["--map", str(path), str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "x 1234 y"


def test_longest_key_first():
    m = _mapping({"ACME": "Pub", "ACME Corp": "Public Co"})
    assert [k for k, _ in m.replace][0] == "ACME Corp"
    assert anon.anonymise_text("ACME Corp and ACME", m) == ("Public Co and Pub", 2)


def test_case_sensitive_by_default_and_ignore_case_list():
    cs = _mapping({"Globex": "Initech"})
    assert anon.anonymise_text("globex GLOBEX", cs) == ("globex GLOBEX", 0)
    ic = _mapping({"Globex": "Initech"}, ignore_case=["Globex"])
    assert anon.anonymise_text("GLOBEX globex Globex", ic) == (
        "Initech Initech Initech",
        3,
    )


def test_single_pass_does_not_chain():
    m = _mapping({"Alpha": "Beta", "Beta": "Gamma"})
    assert anon.anonymise_text("Alpha", m) == ("Beta", 1)
    assert anon.anonymise_text("Alpha Beta", m) == ("Beta Gamma", 2)


def test_check_exit_codes_and_no_modification(tmp_path):
    target = tmp_path / "notes.md"
    target.write_text("ACME wrote 12.5 bar\n", encoding="utf-8")
    map_path = _write_map(tmp_path, {"replace": {"ACME": "Pub"}})

    def run(*extra):
        return subprocess.run(
            [sys.executable, str(TOOL), "--map", str(map_path), *extra, str(target)],
            capture_output=True,
            text=True,
        )

    res = run("--check")
    assert res.returncode == 1
    assert "1 replacement" in res.stdout
    assert "Pub" not in res.stdout
    assert target.read_text(encoding="utf-8") == "ACME wrote 12.5 bar\n"

    assert run().returncode == 0
    assert target.read_text(encoding="utf-8") == "Pub wrote 12.5 bar\n"
    assert run("--check").returncode == 0


def test_rename_files_and_directories(tmp_path):
    work = tmp_path / "work"
    (work / "secretdir").mkdir(parents=True)
    (work / "ACME_report.txt").write_text("ACME report", encoding="utf-8")
    (work / "secretdir" / "a.txt").write_text("plain", encoding="utf-8")
    map_path = _write_map(
        tmp_path,
        {"replace": {"ACME": "Pub"}, "rename": {"secretdir": "pubdir"}},
    )
    assert anon.main(["--map", str(map_path), "--rename", str(work)]) == 0
    assert not (work / "ACME_report.txt").exists()
    assert (work / "Pub_report.txt").read_text(encoding="utf-8") == "Pub report"
    assert (work / "pubdir" / "a.txt").exists()
    assert not (work / "secretdir").exists()


def test_ipynb_outputs_are_rewritten(tmp_path):
    nb = {
        "cells": [
            {
                "cell_type": "code",
                "source": ["print('hi')"],
                "outputs": [
                    {"output_type": "stream", "name": "stdout", "text": ["ACME 42\n"]}
                ],
            }
        ],
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {},
    }
    path = tmp_path / "nb.ipynb"
    path.write_text(json.dumps(nb), encoding="utf-8")
    map_path = _write_map(tmp_path, {"replace": {"ACME": "Pub"}})
    assert anon.main(["--map", str(map_path), str(path)]) == 0
    text = path.read_text(encoding="utf-8")
    assert "ACME" not in text
    assert json.loads(text)["cells"][0]["outputs"][0]["text"] == ["Pub 42\n"]


def test_iter_files_skips_vendored_dirs(tmp_path):
    for sub in ("node_modules", ".git", "web/public/py", "keep"):
        d = tmp_path / sub
        d.mkdir(parents=True)
        (d / "f.txt").write_text("x", encoding="utf-8")
    names = {p.relative_to(tmp_path).as_posix() for p in anon.iter_files([tmp_path])}
    assert names == {"keep/f.txt"}
