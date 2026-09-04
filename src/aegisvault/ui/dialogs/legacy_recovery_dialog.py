"""Explicit confirmation for migration-only legacy file recovery."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from aegisvault.i18n.translator import Translator
from aegisvault.ui.light import ensure_light_appearance


class LegacyRecoveryDialog(QDialog):
    """Explain the legacy boundary and require an explicit recovery choice."""

    def __init__(self, parent: QWidget | None, translator: Translator, input_path: Path) -> None:
        super().__init__(parent)
        ensure_light_appearance()
        self.i18n = translator
        self.setModal(True)
        self.resize(600, 280)
        self.setMinimumWidth(440)
        self.setWindowTitle(self.i18n.t("recovery.file_confirm_title"))
        self.setAccessibleName(self.windowTitle())

        layout = QVBoxLayout(self)
        self.body_label = QLabel(self.i18n.t("recovery.file_confirm_body"))
        self.body_label.setWordWrap(True)
        self.path_label = QLabel(self.i18n.t("recovery.file_confirm_path", path=str(input_path)))
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setAccessibleName(self.path_label.text())
        self.warning_label = QLabel(self.i18n.t("recovery.file_confirm_warning"))
        self.warning_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(self)
        self.recover_button = QPushButton(self.i18n.t("action.recover_legacy"), self)
        self.cancel_button = QPushButton(self.i18n.t("action.cancel"), self)
        self.recover_button.setAccessibleName(self.recover_button.text())
        self.cancel_button.setAccessibleName(self.cancel_button.text())
        self.recover_button.setAutoDefault(False)
        self.cancel_button.setAutoDefault(True)
        self.cancel_button.setDefault(True)
        self.buttons.addButton(self.recover_button, QDialogButtonBox.ButtonRole.AcceptRole)
        self.buttons.addButton(self.cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.body_label)
        layout.addWidget(self.path_label)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.buttons)

def confirm_legacy_file_recovery(parent: QWidget, translator: Translator, input_path: Path) -> bool:
    """Return true only after the user accepts the migration-only recovery dialog."""

    dialog = LegacyRecoveryDialog(parent, translator, input_path)
    return dialog.exec() == QDialog.DialogCode.Accepted
