"""Qt stylesheet tokens."""

from __future__ import annotations


def app_stylesheet(theme: str = "dark") -> str:
    return LIGHT_QSS if theme == "light" else DARK_QSS


DARK_QSS = """
* {
  font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  letter-spacing: 0px;
}
QMainWindow, QWidget#Root {
  color: #eef2ff;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #070b18, stop:0.48 #0d1428, stop:1 #101725);
}
QWidget#ScrollContent {
  background: transparent;
}
QFrame#Sidebar {
  background: rgba(8, 13, 28, 0.76);
  border-right: 1px solid rgba(148, 163, 184, 0.16);
}
QFrame#Card, QFrame#DropZone, QFrame#ResultCard {
  background: rgba(20, 29, 50, 0.72);
  border: 1px solid rgba(180, 194, 215, 0.16);
  border-radius: 18px;
}
QFrame#DropZone {
  border-style: dashed;
  border-color: rgba(125, 211, 252, 0.32);
}
QFrame#ResultCard {
  background: rgba(11, 18, 34, 0.70);
}
QLabel#Brand {
  font-size: 24px;
  font-weight: 700;
  color: #f8fafc;
}
QLabel#Subtitle, QLabel#Description, QLabel#Muted {
  color: #9aa8bc;
}
QLabel#PageTitle {
  font-size: 23px;
  font-weight: 700;
  color: #f8fafc;
}
QLabel#StatusBadge {
  padding: 5px 10px;
  border-radius: 9px;
  background: rgba(148, 163, 184, 0.12);
  color: #cbd5e1;
}
QLabel#StatusBadge[state="running"], QLabel#StatusBadge[state="cancelling"] {
  color: #bae6fd;
  background: rgba(14, 165, 233, 0.18);
  border: 1px solid rgba(125, 211, 252, 0.25);
}
QLabel#StatusBadge[state="done"] {
  color: #bbf7d0;
  background: rgba(34, 197, 94, 0.16);
  border: 1px solid rgba(74, 222, 128, 0.24);
}
QLabel#StatusBadge[state="failed"] {
  color: #fecaca;
  background: rgba(239, 68, 68, 0.16);
  border: 1px solid rgba(248, 113, 113, 0.24);
}
QLabel#StatusBadge[state="cancelled"] {
  color: #fde68a;
  background: rgba(245, 158, 11, 0.16);
  border: 1px solid rgba(251, 191, 36, 0.24);
}
QPushButton, QToolButton {
  min-height: 34px;
  padding: 6px 14px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(45, 56, 78, 0.72);
  color: #e2e8f0;
}
QPushButton:hover, QToolButton:hover {
  background: rgba(61, 73, 98, 0.86);
  border-color: rgba(125, 211, 252, 0.42);
}
QPushButton:disabled, QToolButton:disabled {
  color: #64748b;
  background: rgba(26, 35, 54, 0.42);
}
QPushButton#Primary {
  background: #60a5fa;
  color: #06101f;
  border-color: #93c5fd;
  font-weight: 700;
}
QPushButton#Primary:hover {
  background: #93c5fd;
}
QPushButton#Danger {
  color: #fed7aa;
  border-color: rgba(251, 146, 60, 0.42);
}
QPushButton#NavButton {
  text-align: left;
  min-height: 42px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: #cbd5e1;
}
QPushButton#NavButton:hover {
  background: rgba(51, 65, 85, 0.50);
}
QPushButton#NavButton:checked {
  background: rgba(96, 165, 250, 0.18);
  border-color: rgba(147, 197, 253, 0.34);
  color: #f8fafc;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget {
  background: rgba(7, 12, 25, 0.76);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 12px;
  color: #f8fafc;
  selection-background-color: #2563eb;
  padding: 8px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
  border-color: rgba(147, 197, 253, 0.78);
}
QCheckBox {
  color: #cbd5e1;
  spacing: 8px;
}
QProgressBar {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 6px;
  background: rgba(7, 12, 25, 0.70);
  height: 10px;
  text-align: center;
  color: transparent;
}
QProgressBar::chunk {
  border-radius: 6px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #22d3ee);
}
QProgressBar#StrengthBar {
  height: 5px;
}
QScrollArea {
  border: none;
  background: transparent;
}
QMessageBox, QDialog {
  background: #0f172a;
  color: #f8fafc;
}
"""


LIGHT_QSS = """
* {
  font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  letter-spacing: 0px;
}
QMainWindow, QWidget#Root {
  background: #eef2f7;
  color: #111827;
}
QFrame#Sidebar, QFrame#Card, QFrame#DropZone, QFrame#ResultCard {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(71, 85, 105, 0.18);
  border-radius: 18px;
}
QLabel#Brand, QLabel#PageTitle {
  color: #0f172a;
  font-weight: 700;
}
QLabel#Brand { font-size: 24px; }
QLabel#PageTitle { font-size: 23px; }
QLabel#Subtitle, QLabel#Description, QLabel#Muted { color: #64748b; }
QLabel#StatusBadge {
  padding: 5px 10px;
  border-radius: 9px;
  background: #e2e8f0;
  color: #334155;
}
QPushButton, QToolButton {
  min-height: 34px;
  padding: 6px 14px;
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.24);
  background: rgba(241, 245, 249, 0.90);
  color: #0f172a;
}
QPushButton:hover, QToolButton:hover {
  background: #e2e8f0;
  border-color: rgba(2, 132, 199, 0.40);
}
QPushButton#Primary {
  background: #2563eb;
  color: white;
  border-color: #3b82f6;
  font-weight: 700;
}
QPushButton#NavButton {
  text-align: left;
  min-height: 42px;
  background: transparent;
  border: 1px solid transparent;
}
QPushButton#NavButton:checked {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.26);
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QListWidget {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(100, 116, 139, 0.24);
  border-radius: 12px;
  color: #0f172a;
  padding: 8px;
}
QProgressBar {
  border: 1px solid rgba(100, 116, 139, 0.20);
  border-radius: 6px;
  background: rgba(226, 232, 240, 0.82);
  height: 10px;
  color: transparent;
}
QProgressBar::chunk {
  border-radius: 6px;
  background: #2563eb;
}
QScrollArea {
  border: none;
  background: transparent;
}
"""

