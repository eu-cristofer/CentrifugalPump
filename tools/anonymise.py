"""Rewrite names and tags in files from a private map, never touching digits.

Usage::

    python tools/anonymise.py --map MAP.yaml PATH... [--rename] [--check]

Map format (YAML)::

    replace:      {"real string": "public string"}
    rename:       {"real/path": "public/path"}   # path substrings, with --rename
    ignore_case:  ["real string"]                # keys matched case-insensitively

Replacement is a single regex pass (longest key first), so a map such as
``A -> B`` and ``B -> C`` never chains.  A key that is purely numeric (after
dropping whitespace and punctuation) is refused: numbers are never rewritten.
The map itself is confidential and must never be committed.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

import yaml

TEXT_SUFFIXES = frozenset(
    {
        ".pumpflow",
        ".json",
        ".ipynb",
        ".md",
        ".rst",
        ".py",
        ".ts",
        ".tsx",
        ".toml",
        ".yml",
        ".yaml",
        ".txt",
        ".csv",
        ".mjs",
        ".js",
        ".html",
        ".tex",
        ".po",
    }
)
SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", "dist"})
_NON_ALNUM = re.compile(r"[\W_]+")


def _check_key(key: str) -> None:
    squashed = _NON_ALNUM.sub("", key)
    if not squashed:
        raise ValueError("empty or separator-only map key refused")
    if squashed.isdigit():
        raise ValueError("numeric-only map key refused: digits are never rewritten")


@dataclass
class Mapping:
    """A compiled anonymisation map."""

    replace: list[tuple[str, str]]
    ignore_case: set[str] = field(default_factory=set)
    rename: dict[str, str] = field(default_factory=dict)
    _regex: re.Pattern | None = field(init=False, default=None, repr=False)
    _exact: dict[str, str] = field(init=False, default_factory=dict, repr=False)
    _folded: dict[str, str] = field(init=False, default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.replace = sorted(self.replace, key=lambda kv: (-len(kv[0]), kv[0]))
        for key, _ in self.replace:
            _check_key(key)
        for key in self.rename:
            _check_key(key)
        self.ignore_case = {k.lower() for k in self.ignore_case}
        parts = []
        for key, value in self.replace:
            if key.lower() in self.ignore_case:
                parts.append(f"(?i:{re.escape(key)})")
                self._folded[key.lower()] = value
            else:
                parts.append(re.escape(key))
                self._exact[key] = value
        self._regex = re.compile("|".join(parts)) if parts else None


def load_map(path: str | Path) -> Mapping:
    """Read a YAML map file into a :class:`Mapping` (keys sorted longest first)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("map file must be a YAML mapping")
    replace = data.get("replace") or {}
    rename = data.get("rename") or {}
    ignore = data.get("ignore_case") or []
    return Mapping(
        [(str(k), str(v)) for k, v in replace.items()],
        {str(k) for k in ignore},
        {str(k): str(v) for k, v in rename.items()},
    )


def anonymise_text(text: str, mapping: Mapping) -> tuple[str, int]:
    """Apply the map in one pass; return ``(new_text, replacement_count)``."""
    rx = mapping._regex
    if rx is None:
        return text, 0

    def sub(m: re.Match) -> str:
        found = m.group(0)
        value = mapping._exact.get(found)
        return value if value is not None else mapping._folded[found.lower()]

    return rx.subn(sub, text)


def _skipped(p: Path) -> bool:
    return p.name in SKIP_DIRS or p.parts[-3:] == ("web", "public", "py")


def _iter_with_root(paths: Iterable[str | Path]) -> Iterator[tuple[Path, Path]]:
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p.parent, p
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            base = Path(dirpath)
            dirnames[:] = sorted(d for d in dirnames if not _skipped(base / d))
            for name in sorted(filenames):
                yield p, base / name


def iter_files(paths: Iterable[str | Path]) -> Iterator[Path]:
    """Yield files under the given files/directories, skipping vendored dirs."""
    for _, f in _iter_with_root(paths):
        yield f


def _renamed(rel: str, mapping: Mapping) -> str:
    if mapping.rename:
        keys = sorted(mapping.rename, key=len, reverse=True)
        rx = re.compile("|".join(re.escape(k) for k in keys))
        rel = rx.sub(lambda m: mapping.rename[m.group(0)], rel)
    head, _, name = rel.rpartition("/")
    name, _ = anonymise_text(name, mapping)
    return f"{head}/{name}" if head else name


def _is_tracked(p: Path) -> bool:
    try:
        r = subprocess.run(
            ["git", "ls-files", "--error-unmatch", p.name],
            cwd=p.parent,
            capture_output=True,
        )
    except OSError:
        return False
    return r.returncode == 0


def _move(src: Path, dst: Path, root: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"rename target exists for {src}")
    moved = False
    if _is_tracked(src):
        r = subprocess.run(
            ["git", "mv", str(src.resolve()), str(dst.resolve())],
            cwd=src.parent,
            capture_output=True,
        )
        moved = r.returncode == 0
    if not moved:
        os.rename(src, dst)
    p = src.parent
    while p != root and p.is_dir() and not any(p.iterdir()):
        p.rmdir()
        p = p.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--map", required=True, help="YAML map file (private)")
    ap.add_argument("paths", nargs="+", metavar="PATH")
    ap.add_argument("--rename", action="store_true", help="also rename files")
    ap.add_argument("--check", action="store_true", help="report only; exit 1 if any")
    args = ap.parse_args(argv)

    try:
        mapping = load_map(args.map)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (OSError, yaml.YAMLError) as exc:
        print(f"error: cannot load map ({type(exc).__name__})", file=sys.stderr)
        return 2

    files = list(_iter_with_root(args.paths))
    total = changed = renames = 0
    for _, f in files:
        if f.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        new, n = anonymise_text(text, mapping)
        if n:
            total += n
            changed += 1
            print(f"{f}: {n} replacement(s)")
            if not args.check:
                f.write_bytes(new.encode("utf-8"))

    if args.rename:
        for root, f in files:
            rel = f.relative_to(root).as_posix()
            new_rel = _renamed(rel, mapping)
            if new_rel == rel:
                continue
            renames += 1
            print(f"{f}: rename")
            if not args.check:
                try:
                    _move(f, root / new_rel, root)
                except (OSError, FileExistsError) as exc:
                    print(f"error: {exc}", file=sys.stderr)
                    return 2

    if args.check:
        return 1 if (total or renames) else 0
    print(f"{total} replacement(s) in {changed} file(s), {renames} rename(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
