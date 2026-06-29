from __future__ import annotations

import tomllib
from pathlib import Path

import aegisvault
from aegisvault.version import DISPLAY_VERSION, PACKAGE_VERSION, RELEASE_TAG

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_version_matches_display_version() -> None:
    assert aegisvault.__version__ == DISPLAY_VERSION


def test_version_constants_for_100_stable() -> None:
    assert PACKAGE_VERSION == "1.0.0"
    assert DISPLAY_VERSION == "1.0.0"
    assert RELEASE_TAG == "v1.0.0"


def test_pyproject_version_matches_package_version() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == PACKAGE_VERSION
    assert "Development Status :: 5 - Production/Stable" in data["project"]["classifiers"]


def test_docs_reference_display_version() -> None:
    for relative in ["README.md", "CHANGELOG.md", "SECURITY.md", "docs/QA_CHECKLIST.md", "docs/releases/v1.0.0.md"]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert DISPLAY_VERSION in text


def test_public_release_docs_do_not_reference_stale_alpha_line() -> None:
    stale_terms = ["0.4.1-alpha", "0.4.0-alpha", "0.3.0-alpha", "currently `0.3.0-alpha`"]
    for relative in [
        "README.md",
        "SECURITY.md",
        "docs/QA_CHECKLIST.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/releases/v1.0.0.md",
    ]:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for term in stale_terms:
            assert term not in text, f"{relative} still references {term}"


def test_release_artifact_name_is_standardized() -> None:
    expected = "AegisVault-v1.0.0-win64.zip"
    for relative in ["README.md", "docs/RELEASE_CHECKLIST.md", "docs/releases/v1.0.0.md", "scripts/verify_release.ps1"]:
        assert expected in (ROOT / relative).read_text(encoding="utf-8")


def test_build_script_supports_zip_used_by_verify_release() -> None:
    build_text = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    verify_text = (ROOT / "scripts" / "verify_release.ps1").read_text(encoding="utf-8")
    assert "[switch]$Zip" in build_text
    assert ".\\scripts\\build_windows.ps1 -Clean -Zip" in verify_text
