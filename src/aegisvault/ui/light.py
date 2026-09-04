"""A fixed light system palette, without widget skins or font overrides."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def ensure_light_appearance() -> None:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    # Qt 6.9 supports explicitly overriding the platform's requested scheme.
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    palette = app.style().standardPalette()
    # Some platform/offscreen styles keep a dark standard palette. Override
    # only semantic colours; keep native metrics, focus rings and system fonts.
    if palette.color(QPalette.ColorRole.Window).lightness() < 128:
        for role, color in (
            (QPalette.ColorRole.Window, "#f0f0f0"),
            (QPalette.ColorRole.Base, "#ffffff"),
            (QPalette.ColorRole.AlternateBase, "#f5f5f5"),
            (QPalette.ColorRole.Button, "#f0f0f0"),
            (QPalette.ColorRole.ToolTipBase, "#ffffdc"),
            (QPalette.ColorRole.Text, "#000000"),
            (QPalette.ColorRole.WindowText, "#000000"),
            (QPalette.ColorRole.ButtonText, "#000000"),
            (QPalette.ColorRole.ToolTipText, "#000000"),
            (QPalette.ColorRole.Highlight, "#0078d4"),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
            (QPalette.ColorRole.PlaceholderText, "#666666"),
        ):
            palette.setColor(role, QColor(color))
        for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#777777"))
    if app.palette() != palette:
        app.setPalette(palette)
