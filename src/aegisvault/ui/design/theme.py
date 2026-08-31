"""Stylesheet generation for the restrained single-window interface."""

from __future__ import annotations

from aegisvault.ui.design import tokens


def stylesheet(theme: str = "dark") -> str:
    return _light() if theme == "light" else _dark()


def _base() -> str:
    return f"""
* {{
  font-family: {tokens.FONT_FAMILY};
  font-size: {tokens.FONT_SIZE_BODY}px;
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
QWidget#ScrollContent {{
  background: transparent;
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview,
QFrame#TaskProgress, QFrame#ResultSummary, QFrame#AdvancedPanel {{
  border-radius: {tokens.RADIUS_CARD}px;
}}
QFrame#InlineAlert {{
  border-radius: {tokens.RADIUS_CONTROL}px;
}}
QLabel#Brand {{
  font-size: 17px;
  font-weight: 700;
}}
QLabel#PageTitle {{
  font-size: {tokens.FONT_SIZE_TITLE}px;
  font-weight: 700;
}}
QLabel#SectionTitle {{
  font-size: {tokens.FONT_SIZE_SECTION}px;
  font-weight: 600;
}}
QLabel#Muted, QLabel#Description, QLabel#FormLabel, QLabel#MetaLabel, QLabel#WarningText {{
  font-size: {tokens.FONT_SIZE_SMALL}px;
}}
QPushButton#NavButton {{
  min-height: 34px;
  padding: 0 16px;
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
QMenuBar {{
  padding: 2px 8px;
}}
QMenuBar::item, QMenu::item {{
  padding: 6px 10px;
}}
"""


def _dark() -> str:
    return (
        _base()
        + f"""
QMainWindow, QWidget#Root {{
  color: {tokens.TEXT_DARK};
  background: #0c1016;
}}
QFrame#NavigationBar, QFrame#PageHeader, QFrame#StatusArea {{
  background: #111720;
}}
QFrame#NavigationBar, QFrame#PageHeader {{
  border-bottom: 1px solid {tokens.BORDER_DARK};
}}
QFrame#StatusArea {{
  border-top: 1px solid {tokens.BORDER_DARK};
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview,
QFrame#TaskProgress, QFrame#ResultSummary, QFrame#AdvancedPanel {{
  background: #151d28;
  border: 1px solid {tokens.BORDER_DARK};
}}
QFrame#FilePickerCard {{
  background: #111822;
  border-style: dashed;
}}
QLabel#Brand, QLabel#PageTitle, QLabel#SectionTitle {{
  color: #f7f9fc;
}}
QLabel#Description, QLabel#Muted, QLabel#FormLabel, QLabel#MetaLabel {{
  color: {tokens.TEXT_DARK_MUTED};
}}
QLabel#WarningText {{
  color: #f8c66a;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QListWidget {{
  background: #0c121a;
  border: 1px solid {tokens.BORDER_DARK};
  color: {tokens.TEXT_DARK};
  selection-background-color: {tokens.ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QListWidget:focus, QPushButton:focus, QToolButton:focus {{
  border-color: {tokens.ACCENT};
}}
QPushButton, QToolButton {{
  color: {tokens.TEXT_DARK};
  background: #202a38;
  border: 1px solid #344154;
}}
QPushButton:hover, QToolButton:hover {{
  background: #293547;
}}
QPushButton:disabled, QToolButton:disabled {{
  color: #687789;
  background: #151c25;
  border-color: #273140;
}}
QPushButton#Primary {{
  background: {tokens.ACCENT};
  border-color: {tokens.ACCENT_HOVER};
  color: #07111f;
  font-weight: 700;
  min-width: 132px;
}}
QPushButton#Danger {{
  color: #fecaca;
  border-color: #7f1d1d;
}}
QPushButton#NavButton {{
  background: transparent;
  border: 1px solid transparent;
  color: #b9c5d4;
}}
QPushButton#NavButton:checked {{
  background: #223047;
  border-color: #3c4d65;
  color: #ffffff;
}}
QPushButton#SegmentButton {{
  background: #101721;
}}
QPushButton#SegmentButton:checked {{
  background: #25344a;
  border-color: {tokens.ACCENT};
}}
QFrame#InlineAlert {{
  background: #2d171a;
  border: 1px solid #8f2d35;
}}
QLabel#InlineAlertText {{
  color: #fecaca;
}}
QProgressBar {{
  background: #0c121a;
  border: 1px solid {tokens.BORDER_DARK};
}}
QProgressBar::chunk {{
  background: {tokens.ACCENT};
  border-radius: 5px;
}}
QMenuBar, QMenu {{
  background: #111720;
  color: {tokens.TEXT_DARK};
}}
QMenuBar::item:selected, QMenu::item:selected {{
  background: #25344a;
}}
QCheckBox {{
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
  background: #f3f5f8;
}}
QFrame#NavigationBar, QFrame#PageHeader, QFrame#StatusArea {{
  background: #ffffff;
}}
QFrame#NavigationBar, QFrame#PageHeader {{
  border-bottom: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#StatusArea {{
  border-top: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#Card, QFrame#FilePickerCard, QFrame#OutputPreview,
QFrame#TaskProgress, QFrame#ResultSummary, QFrame#AdvancedPanel {{
  background: #ffffff;
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QFrame#FilePickerCard {{
  background: #f8fafc;
  border-style: dashed;
}}
QLabel#Description, QLabel#Muted, QLabel#FormLabel, QLabel#MetaLabel {{
  color: {tokens.TEXT_LIGHT_MUTED};
}}
QLabel#WarningText {{
  color: #9a5b00;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QListWidget {{
  background: #fbfcfe;
  border: 1px solid {tokens.BORDER_LIGHT};
  color: {tokens.TEXT_LIGHT};
  selection-background-color: #8cb4ff;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QListWidget:focus, QPushButton:focus, QToolButton:focus {{
  border-color: #2563eb;
}}
QPushButton, QToolButton {{
  color: {tokens.TEXT_LIGHT};
  background: #f8fafc;
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QPushButton:hover, QToolButton:hover {{
  background: #e9eef5;
}}
QPushButton:disabled, QToolButton:disabled {{
  color: #94a3b8;
  background: #eef2f6;
}}
QPushButton#Primary {{
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
  font-weight: 700;
  min-width: 132px;
}}
QPushButton#Danger {{
  color: #991b1b;
  border-color: #f4a4a4;
}}
QPushButton#NavButton {{
  background: transparent;
  border: 1px solid transparent;
}}
QPushButton#NavButton:checked {{
  background: #e3edff;
  border-color: #b9d0ff;
  color: #173b79;
}}
QPushButton#SegmentButton {{
  background: #f5f7fa;
}}
QPushButton#SegmentButton:checked {{
  background: #e3edff;
  border-color: #2563eb;
}}
QFrame#InlineAlert {{
  background: #fff1f2;
  border: 1px solid #fecdd3;
}}
QLabel#InlineAlertText {{
  color: #9f1239;
}}
QProgressBar {{
  background: #e2e8f0;
  border: 1px solid {tokens.BORDER_LIGHT};
}}
QProgressBar::chunk {{
  background: #2563eb;
  border-radius: 5px;
}}
QMenuBar, QMenu {{
  background: #ffffff;
  color: {tokens.TEXT_LIGHT};
}}
QMenuBar::item:selected, QMenu::item:selected {{
  background: #e3edff;
}}
"""
    )
