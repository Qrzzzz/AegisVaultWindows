"""Shared page helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


def scroll_page() -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    content.setObjectName("ScrollContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(34, 28, 34, 28)
    layout.setSpacing(18)
    scroll.setWidget(content)
    return scroll, layout


def page_header(title: str, description: str) -> QWidget:
    frame = QWidget()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    desc = QLabel(description)
    desc.setObjectName("Description")
    desc.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(desc)
    return frame


def muted(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("Muted")
    return label


def format_size(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{value} B"
        amount /= 1024
    return f"{value} B"


def safe_stat_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


