import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("next_version", ROOT / "scripts" / "next_version.py")
nv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nv)


def compute(tags, message, branch="main", head_tags=()):
    return str(nv.next_version(tags, message, branch, head_tags))


@pytest.mark.parametrize("tags, message, expected", [
    # No tags yet: start from the last version published before tag-based releases
    ([], "Merge pull request #33\n\nMake extras #minor", "0.9.0"),
    ([], "fix #patch", "0.8.5"),
    ([], "breaking #major", "1.0.0"),
    ([], "try #alpha", "0.8.5a1"),
    # Normal bumps from the latest stable tag
    (["v0.9.0"], "x #patch", "0.9.1"),
    (["v0.9.0", "v0.9.1"], "x #minor", "0.10.0"),
    (["v0.9.0", "v0.10.0", "v0.9.1"], "x #patch", "0.10.1"),  # numeric, not string order
    (["v0.9.0"], "x #major", "1.0.0"),
    # Alphas
    (["v0.9.0"], "x #alpha", "0.9.1a1"),
    (["v0.9.0", "v0.9.1a1"], "x #alpha", "0.9.1a2"),
    (["v0.9.0", "v0.9.1a1", "v0.9.1a2"], "x #final", "0.9.1"),
    (["v0.9.0", "v0.9.1a3"], "x #patch", "0.9.1"),
    (["v0.9.0", "v0.9.1a3"], "x #minor", "0.10.0"),
    # Keyword precedence (same order as before): #alpha wins
    (["v0.9.0"], "x #minor #alpha", "0.9.1a1"),
    # Unrelated tags are ignored
    (["v0.9.0", "release-candidate", "vfoo"], "x #patch", "0.9.1"),
])
def test_next_version(tags, message, expected):
    assert compute(tags, message) == expected


def test_alpha_allowed_on_feature_branch():
    assert compute(["v0.9.0"], "x #alpha", branch="feature/thing") == "0.9.1a1"


@pytest.mark.parametrize("keyword", ["#patch", "#minor", "#major", "#final"])
def test_stable_release_only_on_main(keyword):
    with pytest.raises(nv.ReleaseError, match="only allowed on main"):
        compute(["v0.9.0a1"], f"x {keyword}", branch="feature/thing")


def test_final_without_alpha_fails():
    with pytest.raises(nv.ReleaseError, match="#final needs an alpha"):
        compute(["v0.9.0"], "x #final")


def test_no_keyword_fails():
    with pytest.raises(nv.ReleaseError, match="No release keyword"):
        compute(["v0.9.0"], "just a merge")


def test_rerun_reuses_tag_already_on_commit():
    # A re-run of a release whose publish failed must not bump again
    assert compute(["v0.9.0"], "x #minor", head_tags=["v0.9.0"]) == "0.9.0"


def test_cli_against_a_real_repository(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "one")
    git("tag", "v0.9.0")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "two")

    def run(message, branch="main"):
        env = {**os.environ, "COMMIT_MESSAGE": message, "BRANCH": branch}
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "next_version.py")],
                              cwd=tmp_path, env=env, capture_output=True, text=True)

    ok = run("Merge pull request #1\n\nthing #minor")
    assert ok.returncode == 0 and ok.stdout.strip() == "version=0.10.0"

    bad = run("thing #patch", branch="feature/x")
    assert bad.returncode == 1 and "only allowed on main" in bad.stderr

    git("tag", "v0.10.0")  # release tagged this commit; a re-run must reuse it
    assert run("thing #minor").stdout.strip() == "version=0.10.0"
