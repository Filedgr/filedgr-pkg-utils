"""
Computes the version for a release from the existing git tags and the release
keyword in the commit message. Used by .github/workflows/release.yml.

Releases are identified by tags ``vMAJOR.MINOR.PATCH`` (stable) and
``vMAJOR.MINOR.PATCHaN`` (alpha). Keywords, checked in this order:

  #alpha   next alpha: X.Y.ZaN -> X.Y.Za(N+1); stable X.Y.Z -> X.Y.(Z+1)a1.
           Allowed on any branch.
  #major   (X+1).0.0      -- stable keywords are only allowed on main
  #minor   X.(Y+1).0
  #final   promote the latest alpha X.Y.ZaN -> X.Y.Z
  #patch   X.Y.(Z+1); if an alpha of the next patch exists, X.Y.ZaN -> X.Y.Z

Stable bumps start from the latest stable tag. With no tags at all, the last
version published before tag-based releases (BASELINE) is the starting point.

If the commit being released already carries a version tag (e.g. a re-run of
a release whose publish step failed), that version is reused.

CLI: reads COMMIT_MESSAGE and BRANCH from the environment, prints
``version=X.Y.Z`` (for $GITHUB_OUTPUT), exits 1 with a message on error.
"""
import os
import re
import subprocess
import sys
from typing import Iterable, List, NamedTuple, Optional

BASELINE = "0.8.4"
KEYWORDS = ("#alpha", "#major", "#minor", "#final", "#patch")
_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:a(\d+))?$")


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    alpha: Optional[int] = None  # None = stable

    @classmethod
    def parse(cls, text: str) -> Optional["Version"]:
        match = _TAG.match(text.strip())
        if not match:
            return None
        major, minor, patch, alpha = match.groups()
        return cls(int(major), int(minor), int(patch), int(alpha) if alpha else None)

    @property
    def is_alpha(self) -> bool:
        return self.alpha is not None

    @property
    def base(self) -> "Version":
        return Version(self.major, self.minor, self.patch)

    def sort_key(self):
        # An alpha sorts before the stable release of the same number
        return (self.major, self.minor, self.patch, self.alpha if self.is_alpha else float("inf"))

    def __str__(self) -> str:
        core = f"{self.major}.{self.minor}.{self.patch}"
        return f"{core}a{self.alpha}" if self.is_alpha else core


class ReleaseError(Exception):
    pass


def _parse_all(tags: Iterable[str]) -> List[Version]:
    return [v for v in (Version.parse(t) for t in tags) if v is not None]


def next_version(tags: Iterable[str], message: str, branch: str,
                 head_tags: Iterable[str] = ()) -> Version:
    existing_at_head = sorted(_parse_all(head_tags), key=Version.sort_key)
    if existing_at_head:
        return existing_at_head[-1]

    keyword = next((k for k in KEYWORDS if k in message), None)
    if keyword is None:
        raise ReleaseError(f"No release keyword ({', '.join(KEYWORDS)}) in the commit message.")
    if keyword != "#alpha" and branch != "main":
        raise ReleaseError(f"Stable releases ({keyword}) are only allowed on main, not on '{branch}'.")

    versions = sorted(_parse_all(tags), key=Version.sort_key)
    stable = [v for v in versions if not v.is_alpha]
    latest = versions[-1] if versions else Version.parse(BASELINE)
    latest_stable = stable[-1] if stable else Version.parse(BASELINE)

    if keyword == "#alpha":
        if latest.is_alpha:
            return Version(latest.major, latest.minor, latest.patch, latest.alpha + 1)
        return Version(latest.major, latest.minor, latest.patch + 1, 1)
    if keyword == "#major":
        return Version(latest_stable.major + 1, 0, 0)
    if keyword == "#minor":
        return Version(latest_stable.major, latest_stable.minor + 1, 0)
    if keyword == "#final":
        if not latest.is_alpha:
            raise ReleaseError(f"#final needs an alpha to promote, but the latest version is {latest}.")
        return latest.base
    # #patch
    candidate = Version(latest_stable.major, latest_stable.minor, latest_stable.patch + 1)
    return candidate


def _git(*args: str) -> List[str]:
    out = subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    try:
        version = next_version(
            tags=_git("tag", "--list", "v*"),
            message=os.environ.get("COMMIT_MESSAGE", ""),
            branch=os.environ.get("BRANCH", ""),
            head_tags=_git("tag", "--points-at", "HEAD", "--list", "v*"),
        )
    except ReleaseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"version={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
