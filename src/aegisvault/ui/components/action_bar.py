"""Right-aligned action row."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QWidget

from aegisvault.ui.design import spacing


class ActionBar(QWidget):
    def __init__(self, *widgets: QWidget) -> None:
        super().__init__()
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(0, 0, 0, 0)
        self.row_layout.setSpacing(spacing.SM)
        self.row_layout.addStretch(1)
        for widget in widgets:
            self.row_layout.addWidget(widget)
