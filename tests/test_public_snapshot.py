"""tools/make_public_snapshot.sh: one clean commit, or nothing (toy words only)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX shell")

ROOT = Path(__file__).resolve().parents[1]
GIT = [
    "git",
    "-c",
    "user.email=t@example.com",
    "-c",
    "user.name=T",
    "-c",
    "commit.gpgsign=false",
]
COPIED = [
    "tools/leak_scan.py",
    "tools/install_hooks.sh",
    "tools/hooks/pre-push",
    "tools/make_public_snapshot.sh",
]


def _git(cwd, *args):
    return subprocess.run(
        [*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True
    )


@pytest.fixture()
def repo(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    for rel in COPIED:
        target = work / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    (work / "README.md").write_text("# Toy\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "init")
    words = tmp_path / "words.txt"
    words.write_text("Globex\n", encoding="utf-8")
    return work, words, tmp_path / "dest"


def _run(work, dest, words):
    env = dict(
        os.environ,
        PYTHON=sys.executable,
        GIT_AUTHOR_NAME="T",
        GIT_AUTHOR_EMAIL="t@example.com",
    )
    return subprocess.run(
        ["sh", "tools/make_public_snapshot.sh", str(dest), str(words)],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
    )


def test_clean_snapshot(repo):
    work, words, dest = repo
    res = _run(work, dest, words)
    assert res.returncode == 0, res.stderr
    assert _git(dest, "rev-list", "--count", "HEAD").stdout.strip() == "1"
    assert (dest / "README.md").is_file()
    assert _git(dest, "config", "core.hooksPath").stdout.strip() == "tools/hooks"


def test_confidential_word_blocks_snapshot(repo):
    work, words, dest = repo
    (work / "notes.txt").write_text("project Globex\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "leak")
    res = _run(work, dest, words)
    assert res.returncode == 1
    assert not dest.exists()


def test_non_empty_dest_is_refused(repo):
    work, words, dest = repo
    dest.mkdir()
    (dest / "keep.txt").write_text("x", encoding="utf-8")
    res = _run(work, dest, words)
    assert res.returncode == 2
    assert (dest / "keep.txt").is_file()
