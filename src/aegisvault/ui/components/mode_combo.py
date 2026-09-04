"""Native compact choice control; values stay stable across translation."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QSizePolicy


class ModeCombo(QComboBox):
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], current: str, accessible_name: str) -> None:
        super().__init__()
        # Recompute after an in-place language change; the default caches the
        # first (often shorter Chinese) labels and clips English mode names.
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        for label, value in options:
            self.addItem(label, value)
        self.set_current(current)
        self.setAccessibleName(accessible_name)
        self.currentIndexChanged.connect(lambda _index: self.changed.emit(self.current))

    @property
    def current(self) -> str:
        return str(self.currentData())

    def set_current(self, value: str) -> None:
        index = self.findData(value)
        if index >= 0:
            self.setCurrentIndex(index)

    def set_labels(self, options: list[tuple[str, str]], accessible_name: str) -> None:
        for label, value in options:
            index = self.findData(value)
            if index >= 0:
                self.setItemText(index, label)
        self.setAccessibleName(accessible_name)
