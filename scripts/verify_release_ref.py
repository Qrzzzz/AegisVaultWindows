"""Fail-closed validation for a tagged release checkout."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from release_metadata import load_release_metadata

ROOT = Path(__file__).resolve().parents[1]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class RefError(RuntimeError):
    """Raised when the checked-out Git state is not an authorized release ref."""


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RefError(f"git {' '.join(args)} failed: {detail}")
    return result


def verify_release_ref(
    *,
    expected_tag: str,
    expected_commit: str | None,
    default_branch: str,
    require_clean: bool,
) -> str:
    load_release_metadata(expected_tag=expected_tag)
    if not re.fullmatch(r"v[1-9]\d*\.(?:0|[1-9]\d*)", expected_tag):
        raise RefError(f"Release tag must be strict vX.Y, got: {expected_tag!r}")

    tag_ref = f"refs/tags/{expected_tag}"
    if _git("show-ref", "--verify", "--quiet", tag_ref, check=False).returncode != 0:
        raise RefError(f"Release tag does not exist locally: {tag_ref}")
    object_type = _git("cat-file", "-t", tag_ref).stdout.strip()
    if object_type != "tag":
        raise RefError(f"Release tag must be annotated; {tag_ref} is a {object_type!r} object")

    tag_commit = _git("rev-parse", f"{tag_ref}^{{commit}}").stdout.strip().lower()
    head_commit = _git("rev-parse", "HEAD").stdout.strip().lower()
    if not SHA_RE.fullmatch(tag_commit) or tag_commit != head_commit:
        raise RefError(f"Tag/checkout mismatch: {expected_tag} -> {tag_commit}, HEAD -> {head_commit}")

    if expected_commit:
        expected_commit = expected_commit.lower()
        if not SHA_RE.fullmatch(expected_commit):
            raise RefError(f"Expected commit must be a full 40-character SHA: {expected_commit!r}")
        if expected_commit != tag_commit:
            raise RefError(f"Event/tag commit mismatch: event {expected_commit}, tag {tag_commit}")

    remote_default = f"refs/remotes/origin/{default_branch}"
    if _git("show-ref", "--verify", "--quiet", remote_default, check=False).returncode != 0:
        raise RefError(f"Default branch ref is unavailable: {remote_default}")
    if _git("merge-base", "--is-ancestor", tag_commit, remote_default, check=False).returncode != 0:
        raise RefError(f"Tagged commit {tag_commit} is not contained in origin/{default_branch}")

    if require_clean:
        status = _git("status", "--porcelain=v1", "--untracked-files=normal").stdout.strip()
        if status:
            raise RefError(f"Release checkout is not clean:\n{status}")
    return tag_commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-tag", required=True)
    parser.add_argument("--expected-commit")
    parser.add_argument("--default-branch", required=True)
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        commit = verify_release_ref(
            expected_tag=args.expected_tag,
            expected_commit=args.expected_commit,
            default_branch=args.default_branch,
            require_clean=args.require_clean,
        )
    except (OSError, RefError, RuntimeError) as exc:
        parser.error(str(exc))
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"commit={commit}\n")
    print(commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
