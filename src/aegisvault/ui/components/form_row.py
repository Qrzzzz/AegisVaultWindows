"""Consistent label/control form row."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from aegisvault.ui.design import spacing


class FormRow(QWidget):
    def __init__(self, label: str, control: QWidget) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing.MD)
        text = QLabel(label)
        text.setObjectName("FormLabel")
        text.setFixedWidth(spacing.FORM_LABEL_WIDTH)
        layout.addWidget(text)
        layout.addWidget(control, 1)
