"""Tests for tools/leak_scan.py: confidential words are found everywhere.

Toy words only (Globex, X-1234).  Covers text, docx (incl. words split across
runs), hyphen-less spellings, file names, git ranges and the CLI exit codes.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "leak_scan.py"


def _load():
    spec = importlib.util.spec_from_file_location("leak_scan_tool", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["leak_scan_tool"] = mod
    spec.loader.exec_module(mod)
    return mod


leak = _load()
WORDS = ["Globex", "X-1234"]


def _words_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# private list\n\nGlobex\n  X-1234  \n# Initech\n", encoding="utf-8"
    )
    return path


def test_load_words_ignores_comments_and_blanks(tmp_path):
    assert leak.load_words(_words_file(tmp_path / "w.txt")) == WORDS


def test_text_hit_reports_line_number_and_only_the_entry(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("clean\nalso clean\nvendor is GLOBEX inc\n", encoding="utf-8")
    assert leak.scan_path(f, WORDS, tmp_path) == ["notes.txt:3: Globex"]


def test_comment_entries_are_not_matched(tmp_path):
    words = leak.load_words(_words_file(tmp_path / "w.txt"))
    assert leak.scan_text("Initech", words) == []


def test_separator_free_spellings_match():
    for spelling in ("X1234", "x_1234", "x.1234", "X 1234", "x-1234"):
        assert leak.scan_text(f"ref {spelling} here", WORDS) == [(1, "X-1234")]


def test_short_entries_do_not_use_squashed_matching():
    assert leak.scan_text("code a1 here", ["A-1"]) == []
    assert leak.scan_text("code A-1 here", ["A-1"]) == [(1, "A-1")]


def test_file_name_hit(tmp_path):
    f = tmp_path / "Globex_notes.txt"
    f.write_text("clean", encoding="utf-8")
    assert leak.scan_path(f, WORDS, tmp_path) == ["Globex_notes.txt:name: Globex"]


def test_docx_hit_and_split_runs(tmp_path):
    from docx import Document

    plain = Document()
    plain.add_paragraph("Visit GLOBEX today")
    plain.save(tmp_path / "memo.docx")
    hits = leak.scan_path(tmp_path / "memo.docx", WORDS, tmp_path)
    assert hits == ["memo.docx!word/document.xml: Globex"]

    split = Document()
    para = split.add_paragraph()
    para.add_run("Glo")
    para.add_run("bex")
    split.save(tmp_path / "split.docx")
    hits = leak.scan_path(tmp_path / "split.docx", WORDS, tmp_path)
    assert hits == ["split.docx!word/document.xml: Globex"]


def test_clean_docx_has_no_hits(tmp_path):
    from docx import Document

    doc = Document()
    doc.add_paragraph("Nothing to see")
    doc.save(tmp_path / "clean.docx")
    assert leak.scan_path(tmp_path / "clean.docx", WORDS, tmp_path) == []


def test_binary_file_is_skipped(tmp_path):
    f = tmp_path / "blob.bin"
    f.write_bytes(b"\xff\xfe\x00Globex\xff")
    assert leak.scan_path(f, WORDS, tmp_path) == []


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.com",
            "-c",
            "user.name=T",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _head(cwd: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "notes.txt").write_text("all clean\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "clean start")
    return repo, _head(repo)


def test_git_range_finds_added_line(tmp_path, monkeypatch):
    repo, first = _repo(tmp_path)
    (repo / "notes.txt").write_text("all clean\nGlobex was here\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "add notes")
    monkeypatch.chdir(repo)
    hits = leak.scan_git_range(f"{first}..HEAD", WORDS)
    assert len(hits) == 1
    assert hits[0].startswith("commit ") and hits[0].endswith(": diff: Globex")
    zero = leak.scan_git_range("0" * 40 + "..HEAD", WORDS)
    assert any(h.endswith(": diff: Globex") for h in zero)


def test_git_range_finds_commit_message_and_file_name(tmp_path, monkeypatch):
    repo, first = _repo(tmp_path)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "mention Globex here")
    (repo / "x1234.txt").write_text("fine\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "second")
    monkeypatch.chdir(repo)
    hits = leak.scan_git_range(f"{first}..HEAD", WORDS)
    assert any(": message: Globex" in h for h in hits)
    assert any(": name: X-1234" in h for h in hits)


def test_git_range_ignores_deleted_file_names(tmp_path, monkeypatch):
    repo, _ = _repo(tmp_path)
    (repo / "Globex.txt").write_text("fine\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add")
    added = _head(repo)
    _git(repo, "rm", "-q", "Globex.txt")
    _git(repo, "commit", "-q", "-m", "remove")
    monkeypatch.chdir(repo)
    assert leak.scan_git_range(f"{added}..HEAD", WORDS) == []


def test_git_range_clean(tmp_path, monkeypatch):
    repo, first = _repo(tmp_path)
    (repo / "more.txt").write_text("harmless\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "more")
    monkeypatch.chdir(repo)
    assert leak.scan_git_range(f"{first}..HEAD", WORDS) == []


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_clean_tree_then_hit(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "ok.txt").write_text("nothing here\n", encoding="utf-8")
    # The word list lives inside the scanned tree: it must skip itself.
    words = _words_file(tree / "words.txt")
    assert _run(tree, "--words", str(words)).returncode == 0
    assert _run(tmp_path, "--words", str(words), str(tree)).returncode == 0

    (tree / "bad.txt").write_text("line\nGlobex\n", encoding="utf-8")
    res = _run(tree, "--words", str(words))
    assert res.returncode == 1
    assert "bad.txt:2: Globex" in res.stdout
    # a single-file argument reports its path, including directories
    res = _run(tmp_path, "--words", str(words), "tree/bad.txt")
    assert "tree/bad.txt:2: Globex" in res.stdout


def test_cli_missing_word_list_is_usage_error(tmp_path):
    res = _run(tmp_path, "--words", str(tmp_path / "missing.txt"))
    assert res.returncode == 2
