"""Application shell with sidebar, header, workspace and status area."""

from __future__ import annotations

from PySide6.QtCore import Signal
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

from aegisvault.ui.design import spacing, tokens


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
        layout.setContentsMargins(spacing.PAGE_MARGIN, spacing.LG, spacing.PAGE_MARGIN, spacing.LG)
        layout.setSpacing(spacing.XS)
        layout.addWidget(self.title)
        layout.addWidget(self.description)

    def set_page(self, title: str, description: str) -> None:
        self.title.setText(title)
        self.description.setText(description)


class Sidebar(QFrame):
    page_selected = Signal(int)
    about_requested = Signal()

    def __init__(self, title: str, subtitle: str, nav_items: list[tuple[str, int]], about_label: str) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(tokens.SIDEBAR_WIDTH)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[int, QPushButton] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(spacing.XL, spacing.XL, spacing.XL, spacing.XL)
        layout.setSpacing(spacing.SM)
        brand = QLabel(title)
        brand.setObjectName("Brand")
        desc = QLabel(subtitle)
        desc.setObjectName("Subtitle")
        desc.setWordWrap(True)
        layout.addWidget(brand)
        layout.addWidget(desc)
        layout.addSpacing(spacing.LG)
        for label, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self.page_selected.emit(i))
            self.group.addButton(button)
            self.buttons[index] = button
            layout.addWidget(button)
        layout.addStretch(1)
        about = QPushButton(about_label)
        about.clicked.connect(self.about_requested.emit)
        layout.addWidget(about)
        self.set_current(0)

    def set_current(self, index: int) -> None:
        if index in self.buttons:
            self.buttons[index].setChecked(True)


class StatusArea(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("StatusArea")
        self.label = QLabel("Ready")
        self.label.setObjectName("Muted")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(spacing.PAGE_MARGIN, spacing.SM, spacing.PAGE_MARGIN, spacing.SM)
        layout.addWidget(self.label)

    def show_message(self, message: str, _timeout: int = 0) -> None:
        self.label.setText(message)


class AppShell(QWidget):
    def __init__(self, sidebar: Sidebar) -> None:
        super().__init__()
        self.setObjectName("Root")
        self.sidebar = sidebar
        self.header = PageHeader()
        self.stack = QStackedWidget()
        self.status = StatusArea()
        workspace = QFrame()
        workspace.setObjectName("Workspace")
        work_layout = QVBoxLayout(workspace)
        work_layout.setContentsMargins(0, 0, 0, 0)
        work_layout.setSpacing(0)
        work_layout.addWidget(self.header)
        work_layout.addWidget(self.stack, 1)
        work_layout.addWidget(self.status)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(workspace, 1)
