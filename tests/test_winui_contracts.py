"""Architectural boundaries and localization completeness of the replacement UI."""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backend_has_no_gui_imports_or_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not any("pyside" in value.casefold() or "qt" in value.casefold() for value in project["project"]["dependencies"])
    for path in (ROOT / "src/aegisvault").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"(?:from|import) (?:PySide|PyQt|aegisvault.ui)", source), path
    assert not list((ROOT / "src/aegisvault/ui").rglob("*.py"))
    assert not list((ROOT / "src").rglob("*.qss"))


def test_winui_locales_cover_literal_ui_and_error_keys() -> None:
    app = ROOT / "src/AegisVault.App"
    english = json.loads((app / "Assets/en-US.json").read_text(encoding="utf-8"))
    chinese = json.loads((app / "Assets/zh-CN.json").read_text(encoding="utf-8"))
    assert english.keys() == chinese.keys()
    sources = "\n".join(path.read_text(encoding="utf-8") for path in app.rglob("*")
                        if path.suffix in {".cs", ".xaml"} and not {"obj", "bin"}.intersection(path.parts))
    keys = set(re.findall(r'\bL\["([^"\]]+)"\]|Binding L\[([^\]]+)\]', sources))
    required = {left or right for left, right in keys}
    for path in (ROOT / "src/aegisvault").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        required.update("error." + code for code in re.findall(r'code="([^"]+)"', source))
    for language, messages in (("en-US", english), ("zh-CN", chinese)):
        assert not required - messages.keys(), f"{language}: {sorted(required - messages.keys())}"
        assert all(messages[key].strip() for key in required)
