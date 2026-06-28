"""Qt stylesheet entrypoint."""

from __future__ import annotations

from aegisvault.ui.design.theme import stylesheet


def app_stylesheet(theme: str = "dark") -> str:
    return stylesheet(theme)
