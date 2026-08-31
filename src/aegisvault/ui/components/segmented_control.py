"""Small exclusive segmented button group."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], current: str, accessible_name: str = "") -> None:
        super().__init__()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons: dict[str, QPushButton] = {}
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setAccessibleName(accessible_name)
        for label, value in items:
            button = QPushButton(label)
            button.setObjectName("SegmentButton")
            button.setCheckable(True)
            button.setAccessibleName(label)
            button.clicked.connect(lambda _checked=False, selected=value: self._select(selected))
            self.group.addButton(button)
            self.buttons[value] = button
            self._layout.addWidget(button)
        self.set_current(current, emit=False)

    @property
    def current(self) -> str:
        for value, button in self.buttons.items():
            if button.isChecked():
                return value
        return next(iter(self.buttons))

    def set_labels(self, items: list[tuple[str, str]], accessible_name: str = "") -> None:
        for label, value in items:
            if value in self.buttons:
                self.buttons[value].setText(label)
                self.buttons[value].setAccessibleName(label)
        if accessible_name:
            self.setAccessibleName(accessible_name)

    def set_current(self, value: str, *, emit: bool = True) -> None:
        if value not in self.buttons:
            return
        changed = self.current != value
        self.buttons[value].setChecked(True)
        if emit and changed:
            self.changed.emit(value)

    def _select(self, value: str) -> None:
        self.set_current(value)
