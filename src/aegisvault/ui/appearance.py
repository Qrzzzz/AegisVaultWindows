"""Fluent-inspired Qt styling, with explicit light/dark and system appearance."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


def apply_appearance(theme: str = "light") -> None:
    app = QApplication.instance()
    if not isinstance(app, QApplication) or app.property("appearanceUpdating"):
        return
    app.setProperty("appearanceUpdating", True)
    try:
        scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(theme, Qt.ColorScheme.Unknown)
        app.styleHints().setColorScheme(scheme)
        dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        if theme != "system":
            dark = theme == "dark"
        colors = (
            ("#202328", "#292c31", "#32353a", "#f4f5f7", "#b7bec8", "#464b53", "#383f49", "#86c7ff", "#102b43", "#8b929c", "#243a50", "#ffb4ab")
            if dark else
            ("#eef1f5", "#f8f9fb", "#ffffff", "#202329", "#606671", "#e1e4e9", "#e0e5eb", "#005fb8", "#ffffff", "#8d939b", "#edf4fc", "#a4262c")
        )
        shell, page, card, ink, muted, line, selected, accent, on_accent, edge, note, error = colors
        palette = QPalette()
        for role, value in (
            (QPalette.ColorRole.Window, page), (QPalette.ColorRole.WindowText, ink),
            (QPalette.ColorRole.Base, card), (QPalette.ColorRole.AlternateBase, shell),
            (QPalette.ColorRole.Text, ink), (QPalette.ColorRole.Button, card),
            (QPalette.ColorRole.ButtonText, ink), (QPalette.ColorRole.Highlight, accent),
            (QPalette.ColorRole.HighlightedText, on_accent), (QPalette.ColorRole.PlaceholderText, muted),
            (QPalette.ColorRole.ToolTipBase, card), (QPalette.ColorRole.ToolTipText, ink),
            (QPalette.ColorRole.Link, accent),
        ):
            palette.setColor(role, QColor(value))
        for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(muted))
        app.setPalette(palette)
        if not app.property("fluentFontInitialized"):
            font = QFont(app.font())
            font.setPointSizeF(max(font.pointSizeF(), 10.5))
            app.setFont(font)
            app.setProperty("fluentFontInitialized", True)
        stylesheet = f"""
QMainWindow, QWidget#Shell, QWidget#Sidebar {{ background: {shell}; }}
QWidget#WorkspaceStack {{ background: {page}; border: 1px solid {line}; border-radius: 8px; }}
QWidget#TextPage, QWidget#FilePage, QWidget#Base64Page, QWidget#ScrollContent {{ background: {page}; }}
QDialog {{ background: {page}; }}
QLabel {{ background: transparent; color: {ink}; }}
QLabel[muted="true"], QLabel#Muted {{ color: {muted}; }}
QPushButton, QToolButton {{ background: {card}; border: 1px solid {line}; border-radius: 4px; padding: 7px 16px; color: {ink}; }}
QPushButton:hover, QToolButton:hover {{ background: {selected}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {shell}; }}
QPushButton:focus, QToolButton:focus {{ border: 2px solid {accent}; padding: 6px 15px; }}
QPushButton:disabled, QToolButton:disabled {{ color: {muted}; background: {shell}; }}
QPushButton[primary="true"] {{ color: {on_accent}; background: {accent}; border-color: {accent}; }}
QPushButton[primary="true"]:hover {{ background: {ink}; color: {card}; border-color: {ink}; }}
QPushButton[primary="true"]:focus {{ border: 2px solid {ink}; }}
QPushButton[primary="true"]:disabled {{ color: {muted}; background: {selected}; border-color: {line}; }}
QPushButton[quiet="true"], QToolButton[quiet="true"] {{ background: transparent; border-color: transparent; color: {muted}; }}
QPushButton[quiet="true"]:hover, QToolButton[quiet="true"]:hover {{ background: {selected}; color: {ink}; }}
QPushButton[quiet="true"]:focus, QToolButton[quiet="true"]:focus {{ border-color: {accent}; }}
QToolButton[navigation="true"] {{ background: transparent; border: 0; border-left: 3px solid transparent; text-align: left; padding: 10px 12px; }}
QToolButton[navigation="true"]:hover {{ background: {selected}; }}
QToolButton[navigation="true"]::menu-indicator {{ image: none; width: 0; }}
QToolButton[navigation="true"]:checked {{ background: {selected}; border-left-color: {accent}; }}
QToolButton[navigation="true"]:focus {{ border: 1px solid {accent}; border-left: 3px solid {accent}; padding: 9px 11px; }}
QWidget#ModeSwitch {{ background: {shell}; border: 1px solid {line}; border-radius: 6px; }}
QPushButton[segment="true"] {{ background: transparent; border-color: transparent; padding: 5px 22px; }}
QPushButton[segment="true"]:checked {{ background: {card}; border-color: {line}; }}
QPushButton[segment="true"]:focus {{ border-color: {accent}; padding: 4px 21px; }}
QPushButton[segment="true"]:disabled {{ color: {muted}; }}
QLineEdit, QPlainTextEdit, QListWidget, QComboBox {{ background: {card}; color: {ink}; border: 1px solid {line}; border-bottom: 1px solid {edge}; border-radius: 4px; padding: 7px 10px; selection-background-color: {accent}; selection-color: {on_accent}; }}
QLineEdit:focus, QPlainTextEdit:focus, QListWidget:focus, QComboBox:focus {{ border-bottom: 2px solid {accent}; }}
QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{ color: {muted}; background: {shell}; }}
QLineEdit[outputPath="true"] {{ background: transparent; border: 0; padding: 2px 0; color: {muted}; }}
QLineEdit[outputPath="true"]:focus {{ border-bottom: 1px solid {accent}; }}
QComboBox {{ padding-right: 24px; }}
QComboBox::drop-down {{ border: 0; width: 24px; }}
QComboBox QAbstractItemView {{ background: {card}; color: {ink}; selection-background-color: {selected}; selection-color: {ink}; }}
QWidget#PasswordRow {{ background: {card}; border: 1px solid {line}; border-bottom-color: {edge}; border-radius: 4px; }}
QWidget#PasswordRow QLineEdit {{ background: transparent; border: 0; }}
QWidget#PasswordRow QLineEdit:focus {{ border-bottom: 2px solid {accent}; }}
QWidget#PasswordRow QPushButton {{ background: transparent; border: 1px solid transparent; padding: 6px; }}
QWidget#PasswordRow QPushButton:focus {{ border-color: {accent}; }}
QWidget#FilePicker, QWidget[card="true"] {{ background: {card}; border: 1px solid {line}; border-radius: 6px; }}
QWidget#OutputPreview QPlainTextEdit {{ background: transparent; border: 0; }}
QWidget#OutputPreview QPlainTextEdit:focus {{ border-bottom: 2px solid {accent}; }}
QFrame#InlineAlert {{ background: {note}; border: 1px solid {line}; border-radius: 5px; padding: 8px; }}
QLabel#InlineAlertText, QLabel#WarningText {{ color: {error}; }}
QFrame#InlineAlert:focus {{ border-color: {accent}; }}
QProgressBar {{ background: {selected}; color: {ink}; border: 0; border-radius: 3px; text-align: center; min-height: 6px; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}
QScrollArea {{ background: transparent; border: 0; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {edge}; border-radius: 3px; min-height: 28px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QMenu {{ background: {card}; color: {ink}; border: 1px solid {line}; padding: 5px; }}
QMenu::item {{ padding: 8px 24px; border-radius: 3px; }}
QMenu::item:selected {{ background: {selected}; }}
QMenu::separator {{ height: 1px; background: {line}; margin: 5px; }}
QToolTip {{ background: {card}; color: {ink}; border: 1px solid {line}; padding: 5px; }}
QStatusBar {{ background: {shell}; color: {muted}; }}
"""
        if app.styleSheet() != stylesheet:
            app.setStyleSheet(stylesheet)
        app.setProperty("appearanceDark", dark)
    finally:
        app.setProperty("appearanceUpdating", False)
