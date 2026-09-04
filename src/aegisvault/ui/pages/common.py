"""Shared page helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtGui import QFont, QPalette, QResizeEvent
from PySide6.QtWidgets import (
    QBoxLayout,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class Section(QWidget):
    """A titled section without a decorative group-box outline."""

    def __init__(self) -> None:
        super().__init__()
        self.title = QLabel()
        self.title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        font = QFont(self.title.font())
        font.setWeight(QFont.Weight.Medium)
        self.title.setFont(font)
        self.title.hide()
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(10)
        self.outer.addWidget(self.title)

    def setTitle(self, text: str) -> None:  # noqa: N802
        self.title.setText(text)
        self.title.setVisible(bool(text))
        self.setAccessibleName(text)


class AdaptiveRow(QWidget):
    """Wrap a small row vertically when translated controls no longer fit."""

    def __init__(self, *widgets: QWidget) -> None:
        super().__init__()
        self.widgets = widgets
        self.row = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(10)
        for widget in widgets:
            self.row.addWidget(widget)
        if all(isinstance(widget, QPushButton) for widget in widgets):
            for widget in widgets:
                widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            self.row.addStretch(1)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        hint = super().minimumSizeHint()
        hint.setWidth(max(widget.minimumSizeHint().width() for widget in self.widgets))
        return hint

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        required = sum(widget.sizeHint().width() for widget in self.widgets) + 10 * (len(self.widgets) - 1)
        self.row.setDirection(QBoxLayout.Direction.TopToBottom if self.width() < required else QBoxLayout.Direction.LeftToRight)


class PageHeader(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.title = QLabel()
        font = QFont(self.title.font())
        font.setPointSizeF(font.pointSizeF() * 2)
        font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(font)
        self.description = QLabel()
        self.description.setProperty("muted", True)
        self.description.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(5)
        layout.addWidget(self.title)
        layout.addWidget(self.description)

    def set_texts(self, title: str, description: str) -> None:
        self.title.setText(title)
        self.description.setText(description)


class WorkspacePage(QWidget):
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        layout = self.layout()
        if layout is not None:
            margin = 20 if self.width() < 600 else 32
            layout.setContentsMargins(margin, 24, margin, 24)
        self.update_editor_height()
        shortcut = self.findChild(QLabel, "ShortcutHint")
        if shortcut is not None:
            shortcut.setVisible(self.width() >= 600)

    def update_editor_height(self) -> None:
        editor = getattr(self, "input", None)
        result = getattr(self, "result_scroll", None)
        if editor is not None:
            has_result = result is not None and not result.isHidden()
            editor.setMaximumHeight(100 if has_result else 120 if self.height() < 550 else 210)


def action_row(run: QPushButton, clear: QPushButton) -> QHBoxLayout:
    run.setProperty("primary", True)
    clear.setProperty("quiet", True)
    layout = QHBoxLayout()
    layout.setSpacing(10)
    layout.addWidget(run)
    layout.addWidget(clear)
    layout.addStretch(1)
    shortcut = QLabel("Ctrl + Enter")
    shortcut.setObjectName("ShortcutHint")
    shortcut.setProperty("muted", True)
    layout.addWidget(shortcut)
    return layout


class ContentScrollArea(QScrollArea):
    """Use the form's natural height, with scrolling when the window is small."""

    def sizeHint(self) -> QSize:  # noqa: N802
        content = self.widget()
        return content.sizeHint() if content is not None else super().sizeHint()

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(0, 0)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        content = self.widget()
        if content is not None and watched is content and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)


def scroll_page() -> tuple[QScrollArea, QVBoxLayout]:
    scroll = ContentScrollArea()
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setBackgroundRole(QPalette.ColorRole.Window)
    content = QWidget()
    content.setObjectName("ScrollContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(24)
    scroll.setWidget(content)
    content.installEventFilter(scroll)
    return scroll, layout


def result_area(*widgets: QWidget) -> QScrollArea:
    scroll, layout = scroll_page()
    scroll.setMinimumHeight(112)
    for widget in widgets:
        layout.addWidget(widget, 1)
    scroll.hide()
    return scroll


def form_group() -> tuple[Section, QFormLayout]:
    group = Section()
    group.setProperty("card", True)
    group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    group.outer.setContentsMargins(16, 14, 16, 14)
    form = QFormLayout()
    group.outer.addLayout(form)
    form.setContentsMargins(0, 0, 0, 0)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(10)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    return group, form


def input_group(widget: QWidget) -> Section:
    group = Section()
    group.outer.addWidget(widget)
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
