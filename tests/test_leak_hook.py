"""The pre-push leak guard blocks confidential words (toy word list only).

Covers tools/hooks/pre-push against a bare tmp remote and tools/install_hooks.sh.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX sh hook; not run on Windows"
)

ROOT = Path(__file__).resolve().parent.parent
GIT_ID = [
    "-c",
    "user.email=t@example.com",
    "-c",
    "user.name=T",
    "-c",
    "commit.gpgsign=false",
]


def _git(cwd, *args, env=None, check=True):
    return subprocess.run(
        ["git", *GIT_ID, *args],
        cwd=cwd,
        env=env if env is not None else os.environ,
        capture_output=True,
        text=True,
        check=check,
    )


def _install_tools(repo: Path, with_installer: bool = False) -> None:
    (repo / "tools" / "hooks").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "tools" / "leak_scan.py", repo / "tools" / "leak_scan.py")
    hook = repo / "tools" / "hooks" / "pre-push"
    shutil.copy(ROOT / "tools" / "hooks" / "pre-push", hook)
    hook.chmod(0o755)
    if with_installer:
        shutil.copy(
            ROOT / "tools" / "install_hooks.sh", repo / "tools" / "install_hooks.sh"
        )


@pytest.fixture
def setup(tmp_path):
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    work.mkdir()
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(work, "init", "-b", "main")
    _git(work, "remote", "add", "origin", str(remote))
    _install_tools(work)
    _git(work, "config", "core.hooksPath", "tools/hooks")
    words = tmp_path / "words.txt"
    words.write_text("Globex\nX-1234\n", encoding="utf-8")
    env = {**os.environ, "PUMP_WORDLIST": str(words), "PYTHON": sys.executable}
    env.pop("PUMP_LEAK_SKIP", None)
    return work, remote, env


def _commit(work, env, name, content, message):
    (work / name).write_text(content, encoding="utf-8")
    _git(work, "add", name, env=env)
    _git(work, "commit", "-m", message, env=env)


def _push(work, env):
    return _git(work, "push", "origin", "HEAD:refs/heads/main", env=env, check=False)


def _remote_head(remote, env):
    r = _git(
        remote, "rev-parse", "--verify", "-q", "refs/heads/main", env=env, check=False
    )
    return r.stdout.strip()


def test_clean_first_push_succeeds(setup):
    work, remote, env = setup
    _commit(work, env, "a.txt", "hello pump\n", "add a")
    res = _push(work, env)
    assert res.returncode == 0, res.stderr
    assert _remote_head(remote, env) != ""


def test_leaky_file_blocks_push(setup):
    work, remote, env = setup
    _commit(work, env, "a.txt", "hello pump\n", "add a")
    assert _push(work, env).returncode == 0
    before = _remote_head(remote, env)
    _commit(work, env, "b.txt", "customer is Globex\n", "add b")
    res = _push(work, env)
    assert res.returncode != 0
    assert "blocked" in res.stderr
    assert _remote_head(remote, env) == before


def test_hyphenless_word_in_message_blocks(setup):
    work, remote, env = setup
    _commit(work, env, "a.txt", "hello pump\n", "add a")
    assert _push(work, env).returncode == 0
    before = _remote_head(remote, env)
    _commit(work, env, "b.txt", "clean\n", "note about x1234 unit")
    res = _push(work, env)
    assert res.returncode != 0
    assert _remote_head(remote, env) == before


def test_missing_wordlist_blocks_and_skip_allows(setup, tmp_path):
    work, remote, env = setup
    _commit(work, env, "a.txt", "hello pump\n", "add a")
    env_missing = {**env, "PUMP_WORDLIST": str(tmp_path / "nope.txt")}
    res = _push(work, env_missing)
    assert res.returncode != 0
    assert "PUMP_LEAK_SKIP" in res.stderr
    assert _remote_head(remote, env) == ""

    env_skip = {**env_missing, "PUMP_LEAK_SKIP": "1"}
    res = _push(work, env_skip)
    assert res.returncode == 0, res.stderr
    assert _remote_head(remote, env) != ""


def test_install_hooks_sets_hooks_path(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _install_tools(repo, with_installer=True)
    res = subprocess.run(
        ["sh", "tools/install_hooks.sh"], cwd=repo, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stderr
    cfg = _git(repo, "config", "--get", "core.hooksPath")
    assert cfg.stdout.strip() == "tools/hooks"
