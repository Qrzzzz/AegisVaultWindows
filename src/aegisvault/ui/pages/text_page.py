"""Minimal text encryption workspace."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

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
from aegisvault.ui.components.task_progress import TaskProgress
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import scroll_page


class TextPage(QWidget):
    error = Signal(object, str)
    status_message = Signal(str, int)
    settings_requested = Signal()

    def __init__(self, translator: Translator, settings: AppSettings, service: CryptoService) -> None:
        super().__init__()
        self.setObjectName("TextPage")
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
            self.i18n.t("access.operation_mode"),
        )
        self.mode.changed.connect(self._on_mode_changed)
        self.input = QPlainTextEdit()
        self.input.setMinimumHeight(125)
        self.password = PasswordInput("", "", "", "")
        self.confirm_password = PasswordInput("", "", "", "")
        self.alert = InlineAlert()
        self.progress = TaskProgress(self.i18n)
        self.progress.cancel_button.clicked.connect(self.cancel)
        self.output = OutputPreview("", "", "")
        self.output.use_as_input_requested.connect(self.use_result_as_input)

        self.recovery_card = Card()
        self.recovery_note = QLabel()
        self.recovery_note.setObjectName("WarningText")
        self.recovery_note.setWordWrap(True)
        self.recovery_button = QPushButton()
        self.recovery_button.clicked.connect(self.settings_requested.emit)
        self.recovery_card.content_layout.addWidget(self.recovery_note)
        self.recovery_card.content_layout.addWidget(self.recovery_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.run_button = QPushButton()
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self.run_current)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.mode_card = Card()
        self.mode_card.content_layout.addWidget(self.mode)
        self.input_card = Card()
        self.input_card.content_layout.addWidget(self.input)
        self.password_card = Card()
        self.password_card.content_layout.addWidget(self.password)
        self.password_card.content_layout.addWidget(self.confirm_password)
        self.password_card.content_layout.addWidget(self.recovery_card)
        self.password_card.content_layout.addWidget(ActionBar(self.clear_button, self.run_button))
        layout.addWidget(self.mode_card)
        layout.addWidget(self.input_card)
        layout.addWidget(self.password_card)
        layout.addWidget(self.progress)
        layout.addWidget(self.alert)
        layout.addWidget(self.output)
        layout.addStretch(1)

        self.run_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.run_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.run_shortcut.activated.connect(self.run_current)
        self.cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.cancel_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.cancel_shortcut.activated.connect(self.cancel)
        self.retranslate_ui()
        self._on_mode_changed("encrypt")

    def set_service(self, service: CryptoService) -> None:
        self.service = service

    def retranslate_ui(self) -> None:
        self.mode.set_labels(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            self.i18n.t("access.operation_mode"),
        )
        self.mode_card.set_title(self.i18n.t("flow.mode"))
        self.input_card.set_title(self.i18n.t("flow.input"))
        self.password_card.set_title(self.i18n.t("flow.parameters"))
        self.input.setAccessibleName(self.i18n.t("access.text_input"))
        self.password.set_texts(
            self.i18n.t("field.password"),
            self.i18n.t("field.password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.confirm_password.set_texts(
            self.i18n.t("field.confirm_password"),
            self.i18n.t("field.confirm_password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.recovery_card.set_title(self.i18n.t("recovery.title"))
        self.recovery_button.setText(self.i18n.t("action.recovery_settings"))
        self.recovery_button.setAccessibleName(self.i18n.t("action.recovery_settings"))
        recovery_key = "recovery.ak_enabled" if self.settings.allow_ak_compatibility else "recovery.note"
        self.recovery_note.setText(self.i18n.t(recovery_key))
        self.clear_button.setText(self.i18n.t("action.clear_workspace"))
        self.clear_button.setAccessibleName(self.i18n.t("action.clear_workspace"))
        self.output.set_texts(
            self.i18n.t("action.copy"),
            self.i18n.t("action.clear_result"),
            self.i18n.t("action.use_as_input"),
            self.i18n.t("text.output.placeholder"),
        )
        self.output.set_accessible_name(self.i18n.t("access.text_output"))
        self.progress.retranslate_ui()
        self._on_mode_changed(self.mode.current)

    def run_current(self) -> None:
        if self.controller.busy:
            return
        self.alert.clear()
        if self.mode.current == "encrypt":
            self.encrypt()
        else:
            self.decrypt()

    def encrypt(self) -> None:
        password = self.password.text()
        if password != self.confirm_password.text():
            self.alert.show_message(self.i18n.t("error.validation.password_mismatch"))
            self.confirm_password.edit.setFocus()
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

    def cancel(self) -> None:
        self.controller.cancel()

    def wait_for_task(self, timeout_ms: int = 30_000) -> bool:
        return self.controller.wait_for_finished(timeout_ms)

    def clear(self) -> None:
        if self.controller.busy:
            return
        self.alert.clear()
        self.input.clear()
        self.output.clear()
        self.password.clear()
        self.confirm_password.clear()
        self.input.setFocus()

    def use_result_as_input(self) -> None:
        text = self.output.text()
        if not text or self.controller.busy:
            return
        self.input.setPlainText(text)
        self.output.clear()
        next_mode = "decrypt" if self.mode.current == "encrypt" else "encrypt"
        self.mode.set_current(next_mode)
        self.input.setFocus()

    def swap(self) -> None:
        self.use_result_as_input()

    def focus_initial(self) -> None:
        self.input.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _on_success(self, result: Any) -> None:
        self.progress.reset()
        if hasattr(result, "ciphertext"):
            self.output.set_text(result.ciphertext)
        elif hasattr(result, "plaintext"):
            self.output.set_text(result.plaintext)
            if result.compatibility_warning:
                self.status_message.emit(self.i18n.t(f"warning.{result.compatibility_warning}"), 8000)
        self.status_message.emit(self.i18n.t("status.done"), 3000)
        self.output.editor.setFocus()

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.progress.reset()
        self.alert.show_error(self.i18n, exc)
        self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
        self.status_message.emit(self.i18n.t("status.failed"), 5000)
        self.error.emit(exc, diagnostic)

    def _on_cancelled(self) -> None:
        self.progress.reset()
        self.status_message.emit(self.i18n.t("status.cancelled"), 3000)

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.run_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.mode.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.password.setEnabled(not busy)
        self.confirm_password.setEnabled(not busy and self.mode.current == "encrypt")
        self.recovery_button.setEnabled(not busy)
        self.progress.set_state(state)

    def _on_mode_changed(self, value: str) -> None:
        is_encrypt = value == "encrypt"
        self.confirm_password.setVisible(is_encrypt)
        self.confirm_password.setEnabled(not self.controller.busy and is_encrypt)
        self.recovery_card.setVisible(not is_encrypt)
        self.run_button.setText(self.i18n.t("action.encrypt" if is_encrypt else "action.decrypt"))
        self.run_button.setAccessibleName(self.run_button.text())
        placeholder_key = "text.input.encrypt_placeholder" if is_encrypt else "text.input.decrypt_placeholder"
        self.input.setPlaceholderText(self.i18n.t(placeholder_key))
