from __future__ import annotations

import ast
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_python_files_parse() -> None:
    for base in [ROOT / "src", ROOT / "tests"]:
        for path in base.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def test_pyproject_is_valid_toml() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "aegisvault-desktop"


def test_critical_text_files_are_not_minified_to_single_line() -> None:
    files = [
        "README.md",
        "CHANGELOG.md",
        "docs/QA_CHECKLIST.md",
        "docs/RELEASE_CHECKLIST.md",
        ".github/workflows/ci.yml",
        ".github/workflows/security.yml",
        ".github/workflows/release.yml",
        "scripts/build_windows.ps1",
        "scripts/verify_release.ps1",
        "scripts/publish_github_release.py",
    ]
    for relative in files:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        assert "\n" in text, f"{relative} appears to be a single-line file"
        assert text.endswith("\n"), f"{relative} must end with a newline"


def test_ci_workflow_contains_expected_jobs() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "name: Quality" in text
    assert "runs-on: windows-latest" in text
    assert '["3.11", "3.12", "3.13"]' in text
    assert ".\\scripts\\verify_release.ps1" in text
    assert ".\\scripts\\build_windows.ps1 -Clean -Zip" in text
    assert "requirements-dev.lock" in text


def test_release_workflow_builds_tagged_windows_artifact() -> None:
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "name: Release" in text
    assert "tags:" in text
    assert "v*" in text
    assert ".\\scripts\\verify_release.ps1" in text
    assert "scripts/publish_github_release.py" in text
    assert "steps.metadata.outputs.zip_name" in text
    assert "AegisVault-v1.0.0-win64.zip" not in text
