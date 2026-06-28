"""Stylesheet generation from design tokens."""

from __future__ import annotations

from aegisvault.ui.design import tokens


def stylesheet(theme: str = "dark") -> str:
    """Return a restrained Windows-tool stylesheet."""

    return _light() if theme == "light" else _dark()


def _base() -> str:
    return f"""
* {{
  font-family: {tokens.FONT_FAMILY};
  font-size: {tokens.FONT_SIZE_BODY}px;
  letter-spacing: 0px;
}}
QPushButton, QToolButton {{
  min-height: {tokens.BUTTON_HEIGHT}px;
  padding: 0 12px;
  border-radius: {tokens.RADIUS_CONTROL}px;
}}
QLineEdit, QComboBox {{
  min-height: {tokens.INPUT_HEIGHT}px;
  padding: 0 10px;
  border-radius: {tokens.RADIUS_CONTROL}px;
}}
QPlainTextEdit, QTextEdit, QListWidget {{
  border-radius: {tokens.RADIUS_CONTROL}px;
  padding: 10px;
}}
QScrollArea {{
  border: none;
  background: transparent;
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview, QFrame#TaskProgress, QFrame#ResultSummary {{
  border-radius: {tokens.RADIUS_CARD}px;
}}
QFrame#InlineAlert {{
  border-radius: {tokens.RADIUS_CONTROL}px;
  padding: 8px;
}}
QLabel#PageTitle {{
  font-size: {tokens.FONT_SIZE_TITLE}px;
  font-weight: 700;
}}
QLabel#SectionTitle {{
  font-size: {tokens.FONT_SIZE_SECTION}px;
  font-weight: 650;
}}
QLabel#Muted, QLabel#Description, QLabel#FormLabel, QLabel#MetaLabel {{
  font-size: {tokens.FONT_SIZE_SMALL}px;
}}
QPushButton#NavButton {{
  text-align: left;
  min-height: 40px;
  padding-left: 12px;
}}
QPushButton#SegmentButton {{
  min-height: 34px;
  border-radius: 0;
}}
QProgressBar {{
  height: 10px;
  text-align: center;
  color: transparent;
  border-radius: 5px;
}}
"""


def _dark() -> str:
    return (
        _base()
        + f"""
QMainWindow, QWidget#Root {{
  color: {tokens.TEXT_DARK};
  background: #0b0f16;
}}
QFrame#Sidebar, QFrame#PageHeader, QFrame#StatusArea {{
  background: #0f141d;
  border-right: 1px solid {tokens.BORDER_DARK};
}}
QFrame#PageHeader {{
  border-right: none;
  border-bottom: 1px solid {tokens.BORDER_DARK};
}}
QFrame#StatusArea {{
  border-right: none;
  border-top: 1px solid {tokens.BORDER_DARK};
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview, QFrame#TaskProgress, QFrame#ResultSummary {{
  background: {tokens.SURFACE_DARK_RAISED};
  border: 1px solid {tokens.BORDER_DARK};
}}
QFrame#FilePickerCard {{
  border-style: dashed;
}}
QLabel#Brand, QLabel#PageTitle, QLabel#SectionTitle {{
  color: #f8fafc;
}}
QLabel#Subtitle, QLabel#Description, QLabel#Muted, QLabel#FormLabel, QLabel#MetaLabel {{
  color: {tokens.TEXT_DARK_MUTED};
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QListWidget {{
  background: {tokens.SURFACE_DARK_INSET};
  border: 1px solid {tokens.BORDER_DARK};
  color: {tokens.TEXT_DARK};
  selection-background-color: {tokens.ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
  border-color: {tokens.ACCENT};
}}
QPushButton, QToolButton {{
  color: {tokens.TEXT_DARK};
  background: #202a39;
  border: 1px solid #344154;
}}
QPushButton:hover, QToolButton:hover {{
  background: #293548;
  border-color: #4b5d75;
}}
QPushButton:disabled, QToolButton:disabled {{
  color: #64748b;
  background: #151c27;
  border-color: #263142;
}}
QPushButton#Primary {{
  background: {tokens.ACCENT};
  border-color: {tokens.ACCENT_HOVER};
  color: #07111f;
  font-weight: 700;
}}
QPushButton#Danger {{
  color: #fecaca;
  border-color: #7f1d1d;
}}
QPushButton#NavButton {{
  background: transparent;
  border: 1px solid transparent;
  color: #cbd5e1;
}}
QPushButton#NavButton:checked {{
  background: #1d2a3b;
  border-color: #334155;
  color: #f8fafc;
}}
QPushButton#SegmentButton {{
  background: #111827;
}}
QPushButton#SegmentButton:checked {{
  background: #253349;
  border-color: {tokens.ACCENT};
}}
QFrame#InlineAlert {{
  background: #2b1618;
  border: 1px solid #7f1d1d;
}}
QLabel#InlineAlertText {{
  color: #fecaca;
}}
QProgressBar {{
  background: {tokens.SURFACE_DARK_INSET};
  border: 1px solid {tokens.BORDER_DARK};
}}
QProgressBar::chunk {{
  background: {tokens.ACCENT};
  border-radius: 5px;
}}
QCheckBox {{
  color: {tokens.TEXT_DARK};
  spacing: 8px;
}}
"""
    )


def _light() -> str:
    return (
        _base()
        + f"""
QMainWindow, QWidget#Root {{
  color: {tokens.TEXT_LIGHT};
  background: #eef2f7;
}}
QFrame#Sidebar, QFrame#PageHeader, QFrame#StatusArea {{
  background: {tokens.SURFACE_LIGHT};
  border-right: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#PageHeader {{
  border-right: none;
  border-bottom: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#StatusArea {{
  border-right: none;
  border-top: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview, QFrame#TaskProgress, QFrame#ResultSummary {{
  background: {tokens.SURFACE_LIGHT};
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QLabel#Subtitle, QLabel#Description, QLabel#Muted, QLabel#FormLabel, QLabel#MetaLabel {{
  color: {tokens.TEXT_LIGHT_MUTED};
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QListWidget {{
  background: {tokens.SURFACE_LIGHT_INSET};
  border: 1px solid {tokens.BORDER_LIGHT};
  color: {tokens.TEXT_LIGHT};
}}
QPushButton, QToolButton {{
  color: {tokens.TEXT_LIGHT};
  background: #f8fafc;
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QPushButton:hover, QToolButton:hover {{
  background: #e2e8f0;
}}
QPushButton#Primary {{
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
  font-weight: 700;
}}
QPushButton#NavButton {{
  background: transparent;
  border: 1px solid transparent;
}}
QPushButton#NavButton:checked {{
  background: #e0ecff;
  border-color: #bfdbfe;
}}
QFrame#InlineAlert {{
  background: #fef2f2;
  border: 1px solid #fecaca;
}}
QLabel#InlineAlertText {{
  color: #991b1b;
}}
QProgressBar {{
  background: #e2e8f0;
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QProgressBar::chunk {{
  background: #2563eb;
  border-radius: 5px;
}}
"""
    )
