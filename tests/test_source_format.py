from __future__ import annotations

import ast
import tomllib
from pathlib import Path


def test_python_files_parse() -> None:
    for path in Path("src").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    for path in Path("tests").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def test_pyproject_toml_parses() -> None:
    with Path("pyproject.toml").open("rb") as handle:
        tomllib.load(handle)


def test_workflow_yaml_files_have_normal_line_structure() -> None:
    workflow_dir = Path(".github/workflows")
    if not workflow_dir.exists():
        return
    for path in list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        assert len(lines) > 1, f"{path} appears to be compressed into one line"
        assert "\t" not in text, f"{path} contains tab indentation"
        assert any(line.startswith(("name:", "on:")) for line in lines), f"{path} does not look like a workflow"
