"""Keyboard-accessible exclusive action choices with stable semantic values."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QSizePolicy, QWidget


class ModeSwitch(QWidget):
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current: str, accessible_name: str) -> None:
        super().__init__()
        self.setObjectName("ModeSwitch")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.buttons: list[QPushButton] = []
        self.values = [value for _label, value in options]
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(3)
        for index, (label, _value) in enumerate(options):
            button = QPushButton(label)
            button.setProperty("segment", True)
            button.setCheckable(True)
            self.group.addButton(button, index)
            self.buttons.append(button)
            layout.addWidget(button)
        self.group.idClicked.connect(self.setCurrentIndex)
        self._current = -1
        self.set_current(current)
        self.set_labels(options, accessible_name)

    @property
    def current(self) -> str:
        return self.values[self._current]

    def count(self) -> int:
        return len(self.values)

    def currentText(self) -> str:  # noqa: N802
        return self.buttons[self._current].text()

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        if not 0 <= index < len(self.values) or index == self._current:
            return
        self._current = index
        self.buttons[index].setChecked(True)
        self.setFocusProxy(self.buttons[index])
        self.changed.emit(self.current)

    def set_current(self, value: str) -> None:
        if value in self.values:
            self.setCurrentIndex(self.values.index(value))

    def set_labels(self, options: list[tuple[str, str]], accessible_name: str) -> None:
        for label, value in options:
            button = self.buttons[self.values.index(value)]
            button.setText(label)
            button.setAccessibleName(label)
        self.setAccessibleName(accessible_name)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Left):
            step = 1 if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Right) else -1
            self.setCurrentIndex((self._current + step) % len(self.values))
            self.buttons[self._current].setFocus()
            event.accept()
        else:
            super().keyPressEvent(event)
