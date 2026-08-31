"""Consistent label/control form row."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from aegisvault.ui.design import spacing


class FormRow(QWidget):
    def __init__(self, label: str, control: QWidget) -> None:
        super().__init__()
        self.control = control
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing.MD)
        self.label = QLabel(label)
        self.label.setObjectName("FormLabel")
        self.label.setFixedWidth(spacing.FORM_LABEL_WIDTH)
        self.label.setBuddy(control)
        layout.addWidget(self.label)
        layout.addWidget(control, 1)

    def set_label(self, text: str) -> None:
        self.label.setText(text)
        self.control.setAccessibleName(text)
