"""Find confidential words in files, archives, file names or outgoing commits.

Usage::

    python tools/leak_scan.py --words WORDLIST [PATH...] [--git-range A..B]

The word list has one entry per line (``#`` comments and blank lines ignored).
Matching is case-insensitive and also ignores ``-``, ``_``, ``.`` and spaces
(entry ``X-1234`` also matches ``x1234``).  Only the matched entry is ever
printed, never the surrounding text.  Exit 0 = clean, 1 = hit, 2 = usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Iterator

ZIP_SUFFIXES = frozenset({".docx", ".xlsx", ".pptx"})
SKIP_NAMES = frozenset({".git", "node_modules", "__pycache__"})
_TAGS = re.compile(r"<[^>]+>")
_SEPARATORS = re.compile(r"[-_. ]")
_ZERO_SHA = re.compile(r"^0+$")


def squash(text: str) -> str:
    """Lower-case ``text`` and drop ``-``, ``_``, ``.`` and spaces."""
    return _SEPARATORS.sub("", text).lower()


def load_words(path: str | Path) -> list[str]:
    """Read a word list file, ignoring comments and blank lines."""
    words = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            words.append(entry)
    return words


def scan_text(text: str, words: list[str]) -> list[tuple[int, str]]:
    """Return ``(line_number, entry)`` for each entry found on each line."""
    prepared = [(w, w.lower(), squash(w)) for w in words]
    hits: list[tuple[int, str]] = []
    for no, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        sq = squash(line)
        for word, lw, sw in prepared:
            if lw in low or (len(sw) >= 4 and sw in sq):
                hits.append((no, word))
    return hits


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_zip(path: Path, rel: str, words: list[str]) -> list[str]:
    out: list[str] = []
    try:
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if not info.filename.lower().endswith(".xml"):
                    continue
                xml = zf.read(info).decode("utf-8", errors="ignore")
                plain = _TAGS.sub("", xml)
                joined = plain.replace("\r", "").replace("\n", "")
                entries: list[str] = []
                for candidate in (plain, joined):
                    for _, entry in scan_text(candidate, words):
                        if entry not in entries:
                            entries.append(entry)
                out.extend(f"{rel}!{info.filename}: {e}" for e in entries)
    except (zipfile.BadZipFile, OSError):
        pass
    return out


def scan_path(path: str | Path, words: list[str], root: str | Path) -> list[str]:
    """Scan one file (name and content); return report lines."""
    path = Path(path)
    rel = _display(path, Path(root))
    out = [f"{rel}:name: {entry}" for _, entry in scan_text(rel, words)]
    if path.suffix.lower() in ZIP_SUFFIXES and zipfile.is_zipfile(path):
        out.extend(_scan_zip(path, rel, words))
        return out
    try:
        text = path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return out
    out.extend(f"{rel}:{no}: {entry}" for no, entry in scan_text(text, words))
    return out


def _skipped(p: Path) -> bool:
    return (
        p.name in SKIP_NAMES
        or p.parts[-3:] == ("web", "public", "py")
        or p.parts[-2:] == ("web", "dist")
    )


def _walk(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        dirnames[:] = sorted(d for d in dirnames if not _skipped(base / d))
        for name in sorted(filenames):
            yield base / name


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout


def scan_git_range(rng: str, words: list[str]) -> list[str]:
    """Scan added lines, file names and messages of the commits in ``A..B``."""
    first, _, last = rng.partition("..")
    if not last:
        raise ValueError("git range must look like A..B")
    if not first or _ZERO_SHA.match(first):
        revs = _git("rev-list", last)
    else:
        revs = _git("rev-list", f"{first}..{last}")
    out: list[str] = []
    for sha in revs.split():
        short = sha[:7]
        places = {
            "message": _git("log", "-1", "--format=%B", sha),
            # added, copied, modified or renamed paths: a deleted name leaks nothing
            "name": _git("show", "--name-only", "--diff-filter=d", "--format=", sha),
        }
        diff = _git("show", "--format=", "--unified=0", sha)
        places["diff"] = "\n".join(
            line[1:]
            for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        for where, text in places.items():
            seen: list[str] = []
            for _, entry in scan_text(text, words):
                if entry not in seen:
                    seen.append(entry)
            out.extend(f"commit {short}: {where}: {e}" for e in seen)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--words", required=True, help="word list file (private)")
    ap.add_argument("paths", nargs="*", metavar="PATH")
    ap.add_argument("--git-range", help="scan commits in A..B")
    args = ap.parse_args(argv)

    try:
        words = load_words(args.words)
    except OSError:
        print("error: cannot read the word list", file=sys.stderr)
        return 2
    words_file = Path(args.words).resolve()

    targets = args.paths or ([] if args.git_range else ["."])
    hits: list[str] = []
    for target in targets:
        p = Path(target)
        if p.is_file():
            if p.resolve() != words_file:
                hits += scan_path(p, words, Path("."))
        elif p.is_dir():
            for f in _walk(p):
                if f.resolve() != words_file:
                    hits += scan_path(f, words, p)
        else:
            print(f"error: no such path: {target}", file=sys.stderr)
            return 2
    if args.git_range:
        try:
            hits += scan_git_range(args.git_range, words)
        except (subprocess.CalledProcessError, ValueError, OSError):
            print("error: cannot read the git range", file=sys.stderr)
            return 2

    for line in hits:
        print(line)
    if hits:
        print(f"{len(hits)} hit(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
