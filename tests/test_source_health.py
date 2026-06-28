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
        "scripts/build_windows.ps1",
        "scripts/verify_release.ps1",
    ]
    for relative in files:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        assert "\n" in text, f"{relative} appears to be a single-line file"
        assert text.endswith("\n"), f"{relative} must end with a newline"


def test_ci_workflow_contains_expected_jobs() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "name: CI" in text
    assert "runs-on: windows-latest" in text
    assert "python -m compileall src tests" in text
    assert "ruff check ." in text
    assert "mypy src" in text
    assert "pytest -vv" in text
