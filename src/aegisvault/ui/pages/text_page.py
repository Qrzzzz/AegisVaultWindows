"""Text encryption workspace."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QWidget

from aegisvault.core.exceptions import CompatibilityError, ValidationError
from aegisvault.core.legacy import is_ak_token
from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.glass_card import GlassCard
from aegisvault.ui.components.password_field import PasswordField
from aegisvault.ui.components.result_panel import ResultPanel
from aegisvault.ui.components.status_badge import StatusBadge
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import muted, page_header, scroll_page


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
        self.controller.failed.connect(self.error.emit)
        self.controller.cancelled.connect(self._on_cancelled)
        self.controller.state_changed.connect(self._on_state)
        self._last_action = ""
        scroll, layout = scroll_page()
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        layout.addWidget(page_header(self.i18n.t("text.title"), self.i18n.t("text.description")))
        card = GlassCard()
        self.password = PasswordField(
            self.i18n.t("field.password"),
            self.i18n.t("field.password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(self.i18n.t("text.input.placeholder"))
        self.input.setMinimumHeight(150)
        self.result = ResultPanel(
            self.i18n.t("action.copy"),
            self.i18n.t("action.open_output"),
            self.i18n.t("action.clear"),
            self.i18n.t("text.output.placeholder"),
        )
        self.result.reveal_button.hide()
        self.badge = StatusBadge(self.i18n.t("status.ready"))
        self.encrypt_button = self._button("action.encrypt", primary=True)
        self.decrypt_button = self._button("action.decrypt")
        self.clear_button = self._button("action.clear")
        self.clear_button.clicked.connect(self.clear)
        self.encrypt_button.clicked.connect(self.encrypt)
        self.decrypt_button.clicked.connect(self.decrypt)
        buttons = QHBoxLayout()
        buttons.addWidget(self.encrypt_button)
        buttons.addWidget(self.decrypt_button)
        buttons.addStretch(1)
        buttons.addWidget(self.clear_button)
        card.content_layout.addWidget(self.password)
        card.content_layout.addWidget(muted(self.i18n.t("field.input")))
        card.content_layout.addWidget(self.input)
        card.content_layout.addLayout(buttons)
        card.content_layout.addWidget(self.badge)
        card.content_layout.addWidget(muted(self.i18n.t("field.output")))
        card.content_layout.addWidget(self.result)
        layout.addWidget(card)
        layout.addStretch(1)

    def set_service(self, service: CryptoService) -> None:
        self.service = service

    def encrypt(self) -> None:
        password = self.password.text()
        if not password:
            self.error.emit(ValidationError("Password is required.", code="validation.password_required"), "")
            return
        plaintext = self.input.toPlainText()
        self._last_action = "encrypt"
        self.controller.run(lambda _progress, _token: self.service.encrypt_text(plaintext, password))

    def decrypt(self) -> None:
        ciphertext = self.input.toPlainText()
        if is_ak_token(ciphertext.strip()) and not self.settings.allow_ak_compatibility:
            self.error.emit(CompatibilityError("AK compatibility parsing is disabled.", code="legacy.ak_disabled"), "")
            return
        password = self.password.text()
        if not password and not is_ak_token(ciphertext.strip()):
            self.error.emit(ValidationError("Password is required.", code="validation.password_required"), "")
            return
        self._last_action = "decrypt"
        self.controller.run(lambda _progress, _token: self.service.decrypt_text(ciphertext, password))

    def has_running_task(self) -> bool:
        return self.controller.busy

    def clear(self) -> None:
        self.input.clear()
        self.result.clear()

    def _on_success(self, result: Any) -> None:
        if hasattr(result, "ciphertext"):
            self.result.set_result(result.ciphertext)
        elif hasattr(result, "plaintext"):
            self.result.set_result(result.plaintext)
            if result.compatibility_warning:
                self.status_message.emit(self.i18n.t(f"warning.{result.compatibility_warning}"), 8000)

    def _on_cancelled(self) -> None:
        self.result.set_result(self.i18n.t("status.cancelled"))

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.encrypt_button.setEnabled(not busy)
        self.decrypt_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.badge.set_state(state, self.i18n.t(f"status.{state.value}"))

    def _button(self, key: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(self.i18n.t(key))
        if primary:
            button.setObjectName("Primary")
        return button


