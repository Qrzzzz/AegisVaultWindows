"""Resolve and validate release metadata from the authoritative source file."""

from __future__ import annotations

import argparse
import ast
import json
import re
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "aegisvault" / "version.py"
SEMVER_RE = re.compile(r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$")


class MetadataError(RuntimeError):
    """Raised when release metadata violates the repository contract."""


def _string_constants(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            values[target.id] = node.value.value
    return values


def load_release_metadata(*, expected_tag: str | None = None) -> dict[str, Any]:
    constants = _string_constants(VERSION_FILE)
    required = {"APP_NAME", "PACKAGE_VERSION", "DISPLAY_VERSION", "RELEASE_TAG"}
    missing = sorted(required.difference(constants))
    if missing:
        raise MetadataError(f"Missing version constants in {VERSION_FILE}: {', '.join(missing)}")

    version = constants["PACKAGE_VERSION"]
    if not SEMVER_RE.fullmatch(version):
        raise MetadataError(f"PACKAGE_VERSION must be strict X.Y.Z SemVer, got: {version!r}")
    if constants["DISPLAY_VERSION"] != version:
        raise MetadataError("DISPLAY_VERSION must exactly match PACKAGE_VERSION")

    tag = constants["RELEASE_TAG"]
    if tag != f"v{version}":
        raise MetadataError(f"RELEASE_TAG must be v{version}, got: {tag!r}")
    if expected_tag is not None:
        if not re.fullmatch(r"v(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", expected_tag):
            raise MetadataError(f"Expected tag must be strict vX.Y.Z, got: {expected_tag!r}")
        if expected_tag != tag:
            raise MetadataError(f"Tag/source version mismatch: expected {expected_tag}, source declares {tag}")

    app_name = constants["APP_NAME"]
    if app_name != "AegisVault":
        raise MetadataError(f"APP_NAME must remain the canonical artifact basename 'AegisVault', got: {app_name!r}")

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if pyproject["project"]["version"] != version:
        raise MetadataError("pyproject.toml project.version must match PACKAGE_VERSION")
    if pyproject["project"]["name"] != "aegisvault-desktop":
        raise MetadataError("Unexpected project name in pyproject.toml")

    notes_path = Path("docs") / "releases" / f"v{version}.md"
    if not (ROOT / notes_path).is_file():
        raise MetadataError(f"Release notes are missing: {notes_path.as_posix()}")

    exe_name = f"{app_name}.exe"
    zip_name = f"{app_name}-{tag}-win64.zip"
    sbom_name = f"{app_name}-{tag}.cdx.json"
    checksums_name = "SHA256SUMS"
    return {
        "app_name": app_name,
        "version": version,
        "tag": tag,
        "release_title": f"{app_name} v{version}",
        "exe_name": exe_name,
        "zip_name": zip_name,
        "sbom_name": sbom_name,
        "checksums_name": checksums_name,
        "notes_path": notes_path.as_posix(),
        "artifact_name": f"{app_name}-{tag}-release-candidate",
        "public_assets": [zip_name, sbom_name, checksums_name],
    }


def _write_github_output(path: Path, metadata: dict[str, Any]) -> None:
    keys = (
        "app_name",
        "version",
        "tag",
        "release_title",
        "exe_name",
        "zip_name",
        "sbom_name",
        "checksums_name",
        "notes_path",
        "artifact_name",
    )
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in keys:
            handle.write(f"{key}={metadata[key]}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-tag")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    try:
        metadata = load_release_metadata(expected_tag=args.expected_tag)
    except (KeyError, MetadataError, OSError, SyntaxError, tomllib.TOMLDecodeError) as exc:
        parser.error(str(exc))

    if args.github_output:
        _write_github_output(args.github_output, metadata)
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
