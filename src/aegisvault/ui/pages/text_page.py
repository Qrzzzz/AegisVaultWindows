"""Text encryption workspace."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from aegisvault.core.legacy import is_ak_token
from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.action_bar import ActionBar
from aegisvault.ui.components.card import Card
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.components.output_preview import OutputPreview
from aegisvault.ui.components.password_input import PasswordInput
from aegisvault.ui.components.segmented_control import SegmentedControl
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.design import spacing
from aegisvault.ui.pages.common import scroll_page


class TextPage(QWidget):
    error = Signal(object, str)
    status_message = Signal(str, int)

    def __init__(self, translator: Translator, settings: AppSettings, service: CryptoService) -> None:
        super().__init__()
        self.i18n = translator
        self.settings = settings
        self.service = service
        self.controller = TaskController(self)
        self.controller.succeeded.connect(self._on_success)
        self.controller.failed.connect(self._on_failed)
        self.controller.cancelled.connect(self._on_cancelled)
        self.controller.state_changed.connect(self._on_state)

        self.mode = SegmentedControl(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            "encrypt",
        )
        self.mode.changed.connect(self._on_mode_changed)
        self.alert = InlineAlert()
        self.password = PasswordInput(
            self.i18n.t("field.password"),
            self.i18n.t("field.password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.confirm_password = PasswordInput(
            "Confirm password",
            "Repeat the password before encrypting",
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(self.i18n.t("text.input.placeholder"))
        self.output = OutputPreview(self.i18n.t("action.copy"), self.i18n.t("action.clear"), "Swap")
        self.output.swap_requested.connect(self.swap)
        self.run_button = QPushButton(self.i18n.t("action.encrypt"))
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self.run_current)
        self.clear_button = QPushButton(self.i18n.t("action.clear"))
        self.clear_button.clicked.connect(self.clear)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        password_card = Card("Password")
        password_card.content_layout.addWidget(self.password)
        password_card.content_layout.addWidget(self.confirm_password)
        password_card.content_layout.addWidget(self.alert)
        password_card.content_layout.addWidget(ActionBar(self.clear_button, self.run_button))

        grid = QGridLayout()
        grid.setHorizontalSpacing(spacing.LG)
        grid.setVerticalSpacing(spacing.LG)
        input_card = Card(self.i18n.t("field.input"))
        input_card.content_layout.addWidget(self.input)
        output_card = Card(self.i18n.t("field.output"))
        output_card.content_layout.addWidget(self.output)
        grid.addWidget(input_card, 0, 0)
        grid.addWidget(output_card, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        layout.addWidget(self.mode)
        layout.addWidget(password_card)
        layout.addLayout(grid)
        layout.addStretch(1)
        self._on_mode_changed("encrypt")

    def set_service(self, service: CryptoService) -> None:
        self.service = service

    def run_current(self) -> None:
        self.alert.clear()
        if self.mode.current == "encrypt":
            self.encrypt()
        else:
            self.decrypt()

    def encrypt(self) -> None:
        password = self.password.text()
        if password != self.confirm_password.text():
            self.alert.show_message("Passwords do not match.")
            return
        plaintext = self.input.toPlainText()
        self.controller.run(lambda _progress, _token: self.service.encrypt_text(plaintext, password))

    def decrypt(self) -> None:
        ciphertext = self.input.toPlainText()
        password = self.password.text()
        if not password and is_ak_token(ciphertext.strip()) and self.settings.allow_ak_compatibility:
            password = ""
        self.controller.run(lambda _progress, _token: self.service.decrypt_text(ciphertext, password))

    def has_running_task(self) -> bool:
        return self.controller.busy

    def clear(self) -> None:
        self.alert.clear()
        self.input.clear()
        self.output.clear()
        self.password.clear()
        self.confirm_password.clear()

    def swap(self) -> None:
        text = self.output.text()
        if text:
            self.input.setPlainText(text)
            self.output.clear()

    def _on_success(self, result: Any) -> None:
        if hasattr(result, "ciphertext"):
            self.output.set_text(result.ciphertext)
        elif hasattr(result, "plaintext"):
            self.output.set_text(result.plaintext)
            if result.compatibility_warning:
                self.status_message.emit(self.i18n.t(f"warning.{result.compatibility_warning}"), 8000)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.alert.show_error(self.i18n, exc)
        self.error.emit(exc, diagnostic)

    def _on_cancelled(self) -> None:
        self.output.set_text(self.i18n.t("status.cancelled"))

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.run_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.mode.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.confirm_password.setEnabled(not busy and self.mode.current == "encrypt")

    def _on_mode_changed(self, value: str) -> None:
        is_encrypt = value == "encrypt"
        self.confirm_password.setVisible(is_encrypt)
        self.run_button.setText(self.i18n.t("action.encrypt" if is_encrypt else "action.decrypt"))
        placeholder = self.i18n.t("text.input.placeholder") if is_encrypt else "Paste AGV1 or legacy ciphertext"
        self.input.setPlaceholderText(placeholder)
