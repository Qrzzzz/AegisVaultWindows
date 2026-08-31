"""Compact application shell with three workspace entries and timed status."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from aegisvault.ui.design import spacing


class PageHeader(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("PageHeader")
        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        self.description = QLabel()
        self.description.setObjectName("Description")
        self.description.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.PAGE_MARGIN, spacing.MD, spacing.PAGE_MARGIN, spacing.MD)
        layout.setSpacing(spacing.XS)
        layout.addWidget(self.title)
        layout.addWidget(self.description)

    def set_page(self, title: str, description: str) -> None:
        self.title.setText(title)
        self.title.setAccessibleName(title)
        self.description.setText(description)


class NavigationBar(QFrame):
    page_selected = Signal(int)

    def __init__(self, title: str, nav_items: list[tuple[str, int]]) -> None:
        super().__init__()
        self.setObjectName("NavigationBar")
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[int, QPushButton] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(spacing.PAGE_MARGIN, spacing.SM, spacing.PAGE_MARGIN, spacing.SM)
        layout.setSpacing(spacing.XS)
        self.brand = QLabel(title)
        self.brand.setObjectName("Brand")
        layout.addWidget(self.brand)
        layout.addStretch(1)
        for label, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setAccessibleName(label)
            button.clicked.connect(lambda _checked=False, i=index: self.page_selected.emit(i))
            self.group.addButton(button)
            self.buttons[index] = button
            layout.addWidget(button)
        self.set_current(0)

    def set_labels(self, title: str, nav_items: list[tuple[str, int]]) -> None:
        self.brand.setText(title)
        for label, index in nav_items:
            if index in self.buttons:
                self.buttons[index].setText(label)
                self.buttons[index].setAccessibleName(label)

    def set_current(self, index: int) -> None:
        if index in self.buttons:
            self.buttons[index].setChecked(True)


class StatusArea(QFrame):
    def __init__(self, ready_text: str) -> None:
        super().__init__()
        self.setObjectName("StatusArea")
        self._ready_text = ready_text
        self.label = QLabel(ready_text)
        self.label.setObjectName("Muted")
        self.label.setAccessibleName(ready_text)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.clear_message)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(spacing.PAGE_MARGIN, spacing.SM, spacing.PAGE_MARGIN, spacing.SM)
        layout.addWidget(self.label)

    @property
    def timer(self) -> QTimer:
        return self._timer

    def set_ready_text(self, text: str) -> None:
        showing_ready = self.label.text() == self._ready_text or not self.label.text()
        self._ready_text = text
        if showing_ready:
            self.clear_message()

    def show_message(self, message: str, timeout: int = 0) -> None:
        self._timer.stop()
        self.label.setText(message)
        self.label.setAccessibleName(message)
        if timeout > 0:
            self._timer.start(timeout)

    def clear_message(self) -> None:
        self._timer.stop()
        self.label.setText(self._ready_text)
        self.label.setAccessibleName(self._ready_text)


class AppShell(QWidget):
    def __init__(self, navigation: NavigationBar, ready_text: str) -> None:
        super().__init__()
        self.setObjectName("Root")
        self.navigation = navigation
        self.header = PageHeader()
        self.stack = QStackedWidget()
        self.stack.setObjectName("WorkspaceStack")
        self.status = StatusArea(ready_text)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.navigation)
        layout.addWidget(self.header)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.status)
