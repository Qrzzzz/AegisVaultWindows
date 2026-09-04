"""Minimal text encryption workspace."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.components.mode_switch import ModeSwitch
from aegisvault.ui.components.output_preview import OutputPreview
from aegisvault.ui.components.password_input import PasswordInput, PasswordPair
from aegisvault.ui.components.task_progress import TaskProgress
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import (
    PageHeader,
    WorkspacePage,
    action_row,
    input_group,
    result_area,
    scroll_page,
    tab_order,
)


class TextPage(WorkspacePage):
    error = Signal(object, str)
    status_message = Signal(str, int)

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

        self.mode = ModeSwitch(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            "encrypt",
            self.i18n.t("access.operation_mode"),
        )
        self.mode.changed.connect(self._on_mode_changed)
        self.input = QPlainTextEdit()
        self.input.setTabChangesFocus(True)
        self.input.setMinimumHeight(90)
        self.input.setMaximumHeight(210)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.password = PasswordInput("", "", "", "")
        self.confirm_password = PasswordInput("", "", "", "")
        self.alert = InlineAlert()
        self.progress = TaskProgress(self.i18n)
        self.progress.cancel_button.clicked.connect(self.cancel)
        self.output = OutputPreview("", "", "")
        self.output.use_as_input_requested.connect(self.use_result_as_input)

        self.run_button = QPushButton()
        self.run_button.clicked.connect(self.run_current)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(20)
        outer.addWidget(scroll)
        self.header = PageHeader()
        layout.addWidget(self.header)
        layout.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignLeft)
        self.input_group = input_group(self.input)
        self.input_group.title.setBuddy(self.input)
        layout.addWidget(self.input_group, 1)
        self.password_hint = QLabel()
        self.password_hint.setProperty("muted", True)
        self.password_hint.setWordWrap(True)
        self.parameters_group = PasswordPair(self.password, self.confirm_password, self.password_hint)
        layout.addWidget(self.parameters_group)
        outer.addLayout(action_row(self.run_button, self.clear_button))
        outer.addWidget(self.progress)
        outer.addWidget(self.alert)
        self.result_scroll = result_area(self.output)
        outer.addWidget(self.result_scroll)
        outer.addStretch(1)
        self.output.content_changed.connect(self._sync_result_area)
        tab_order(
            self.mode, self.input, self.password.edit, self.password.toggle,
            self.confirm_password.edit, self.confirm_password.toggle, self.run_button,
            self.clear_button, self.output.editor, self.output.copy_button,
            self.output.clear_button, self.output.use_as_input_button,
        )

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

    def _sync_result_area(self) -> None:
        self.result_scroll.setVisible(bool(self.output.text()))
        self.update_editor_height()

    def retranslate_ui(self) -> None:
        self.mode.set_labels(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            self.i18n.t("access.operation_mode"),
        )
        self.output.setTitle(self.i18n.t("flow.result"))
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
        self.output.set_busy(busy)
        self.progress.set_state(state)

    def _on_mode_changed(self, value: str) -> None:
        is_encrypt = value == "encrypt"
        self.confirm_password.setVisible(is_encrypt)
        self.header.set_texts(
            self.i18n.t("modern.text.encrypt" if is_encrypt else "modern.text.decrypt"),
            self.i18n.t("modern.text.encrypt_description" if is_encrypt else "modern.text.decrypt_description"),
        )
        self.input_group.setTitle(self.i18n.t("modern.input.plaintext" if is_encrypt else "modern.input.ciphertext"))
        self.password_hint.setText(self.i18n.t("modern.password.keep" if is_encrypt else "modern.password.decrypt"))
        self.confirm_password.setEnabled(not self.controller.busy and is_encrypt)
        self.run_button.setText(self.i18n.t("modern.action.encrypt_text" if is_encrypt else "modern.action.decrypt_text"))
        self.run_button.setAccessibleName(self.run_button.text())
        placeholder_key = "text.input.encrypt_placeholder" if is_encrypt else "text.input.decrypt_placeholder"
        self.input.setPlaceholderText(self.i18n.t(placeholder_key))
