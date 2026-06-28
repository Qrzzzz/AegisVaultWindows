from __future__ import annotations

import tomllib
from pathlib import Path

import aegisvault
from aegisvault.version import DISPLAY_VERSION, PACKAGE_VERSION, RELEASE_TAG

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_matches_display_version() -> None:
    assert aegisvault.__version__ == DISPLAY_VERSION


def test_version_constants_for_041_alpha() -> None:
    assert PACKAGE_VERSION == "0.4.1a0"
    assert DISPLAY_VERSION == "0.4.1-alpha"
    assert RELEASE_TAG == "v0.4.1-alpha"


def test_pyproject_version_matches_package_version() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == PACKAGE_VERSION


def test_docs_reference_display_version() -> None:
    for relative in ["README.md", "CHANGELOG.md", "docs/QA_CHECKLIST.md"]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert DISPLAY_VERSION in text
