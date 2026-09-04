"""Shared page helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFormLayout, QFrame, QGroupBox, QScrollArea, QSizePolicy, QVBoxLayout, QWidget


class ContentScrollArea(QScrollArea):
    """Use the form's natural height, with scrolling when the window is small."""

    def sizeHint(self) -> QSize:  # noqa: N802
        content = self.widget()
        return content.sizeHint() if content is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(0, 0)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)


def scroll_page() -> tuple[QScrollArea, QVBoxLayout]:
    scroll = ContentScrollArea()
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setBackgroundRole(QPalette.ColorRole.Window)
    content = QWidget()
    content.setObjectName("ScrollContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    scroll.setWidget(content)
    content.installEventFilter(scroll)
    return scroll, layout


def result_area(*widgets: QWidget) -> QScrollArea:
    scroll, layout = scroll_page()
    for widget in widgets:
        layout.addWidget(widget, 1)
    scroll.hide()
    return scroll


def form_group() -> tuple[QGroupBox, QFormLayout]:
    group = QGroupBox()
    form = QFormLayout(group)
    form.setContentsMargins(12, 12, 12, 12)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(10)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    return group, form


def input_group(widget: QWidget) -> QGroupBox:
    group = QGroupBox()
    layout = QVBoxLayout(group)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)
    layout.addWidget(widget)
    return group


def tab_order(*widgets: QWidget) -> None:
    for first, second in zip(widgets, widgets[1:], strict=False):
        QWidget.setTabOrder(first, second)


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
