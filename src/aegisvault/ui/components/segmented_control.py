"""Small exclusive segmented button group."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], current: str) -> None:
        super().__init__()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for label, value in items:
            button = QPushButton(label)
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, v=value: self._select(v))
            self.group.addButton(button)
            self.buttons[value] = button
            layout.addWidget(button)
        self.set_current(current, emit=False)

    @property
    def current(self) -> str:
        for value, button in self.buttons.items():
            if button.isChecked():
                return value
        return next(iter(self.buttons))

    def set_current(self, value: str, *, emit: bool = True) -> None:
        if value not in self.buttons:
            return
        self.buttons[value].setChecked(True)
        if emit:
            self.changed.emit(value)

    def _select(self, value: str) -> None:
        self.set_current(value)
