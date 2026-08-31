"""Minimal file encryption workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from aegisvault.core.exceptions import AppError, ValidationError
from aegisvault.core.models import FileProcessResult, ProgressEvent, TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import decrypted_output_path, encrypted_output_path
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.action_bar import ActionBar
from aegisvault.ui.components.card import Card
from aegisvault.ui.components.file_picker_card import FilePickerCard
from aegisvault.ui.components.form_row import FormRow
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.components.password_input import PasswordInput
from aegisvault.ui.components.result_summary import ResultSummary
from aegisvault.ui.components.segmented_control import SegmentedControl
from aegisvault.ui.components.task_progress import TaskProgress
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.dialogs.legacy_recovery_dialog import confirm_legacy_file_recovery
from aegisvault.ui.pages.common import format_size, safe_stat_size, scroll_page


class FilePage(QWidget):
    error = Signal(object, str)
    status_message = Signal(str, int)
    reveal_requested = Signal(object)
    file_selected = Signal(object)

    def __init__(self, translator: Translator, settings: AppSettings, service: CryptoService) -> None:
        super().__init__()
        self.setObjectName("FilePage")
        self.i18n = translator
        self.settings = settings
        self.service = service
        self.selected_file: Path | None = None
        self._pending_legacy_request: tuple[Path, str] | None = None
        self.controller = TaskController(self)
        self.controller.progress_changed.connect(self._on_progress)
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
        self.picker = FilePickerCard("", "", "")
        self.picker.file_selected.connect(self.set_file)
        self.password = PasswordInput("", "", "", "")
        self.confirm_password = PasswordInput("", "", "", "")
        self.output_dir = QLineEdit()
        self.output_dir.setReadOnly(True)
        self.output_dir_row = FormRow("", self.output_dir)
        self.output_preview = QLabel()
        self.output_preview.setObjectName("Muted")
        self.output_preview.setWordWrap(True)
        self.overwrite_warning = QLabel()
        self.overwrite_warning.setObjectName("WarningText")
        self.overwrite_warning.setWordWrap(True)
        self.legacy_note = QLabel()
        self.legacy_note.setObjectName("WarningText")
        self.legacy_note.setWordWrap(True)
        self.alert = InlineAlert()
        self.run_button = QPushButton()
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self.run_current)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear_file)
        self.progress = TaskProgress(self.i18n)
        self.progress.cancel_button.clicked.connect(self.cancel)
        self.result = ResultSummary("", "")
        self.result.reveal_requested.connect(self.reveal_requested.emit)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.mode_card = Card()
        self.mode_card.content_layout.addWidget(self.mode)
        self.input_card = Card()
        self.input_card.content_layout.addWidget(self.picker)
        self.parameters_card = Card()
        self.parameters_card.content_layout.addWidget(self.password)
        self.parameters_card.content_layout.addWidget(self.confirm_password)
        self.parameters_card.content_layout.addWidget(self.output_dir_row)
        self.parameters_card.content_layout.addWidget(self.output_preview)
        self.parameters_card.content_layout.addWidget(self.overwrite_warning)
        self.parameters_card.content_layout.addWidget(self.legacy_note)
        self.parameters_card.content_layout.addWidget(ActionBar(self.clear_button, self.run_button))
        layout.addWidget(self.mode_card)
        layout.addWidget(self.input_card)
        layout.addWidget(self.parameters_card)
        layout.addWidget(self.progress)
        layout.addWidget(self.alert)
        layout.addWidget(self.result)
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
        self._refresh_preview()

    def retranslate_ui(self) -> None:
        self.mode.set_labels(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            self.i18n.t("access.operation_mode"),
        )
        self.mode_card.set_title(self.i18n.t("flow.mode"))
        self.input_card.set_title(self.i18n.t("flow.input"))
        self.parameters_card.set_title(self.i18n.t("flow.parameters"))
        self.picker.set_texts(
            self.i18n.t("action.select_file"),
            self.i18n.t("file.no_file"),
            self.i18n.t("file.drop_hint"),
        )
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
        self.output_dir_row.set_label(self.i18n.t("field.output_dir"))
        self.output_dir.setAccessibleName(self.i18n.t("field.output_dir"))
        self.overwrite_warning.setText(self.i18n.t("warning.overwrite_enabled"))
        self.legacy_note.setText(self.i18n.t("recovery.file_note"))
        self.clear_button.setText(self.i18n.t("action.clear_file"))
        self.clear_button.setAccessibleName(self.i18n.t("action.clear_file"))
        self.result.set_texts(self.i18n.t("action.open_output"), self.i18n.t("action.clear_result"))
        self.progress.retranslate_ui()
        self._on_mode_changed(self.mode.current)
        self._refresh_preview()

    def set_file(self, path: object) -> bool:
        if self.controller.busy or not isinstance(path, (str, Path)):
            return False
        file_path = Path(path)
        if not file_path.is_file():
            return False
        self.selected_file = file_path
        self.file_selected.emit(file_path)
        self.result.clear()
        self.alert.clear()
        self._refresh_preview()
        return True

    def clear_file(self) -> None:
        if self.controller.busy:
            return
        self.selected_file = None
        self.picker.clear()
        self.result.clear()
        self.alert.clear()
        self._refresh_preview()
        self.picker.select_button.setFocus()

    def run_current(self) -> None:
        if self.controller.busy:
            return
        self.alert.clear()
        if self.mode.current == "encrypt":
            self.encrypt()
        else:
            self.decrypt()

    def encrypt(self) -> None:
        if not self._validate_ready():
            return
        if self.password.text() != self.confirm_password.text():
            self.alert.show_message(self.i18n.t("error.validation.password_mismatch"))
            self.confirm_password.edit.setFocus()
            return
        input_path = self.selected_file
        assert input_path is not None
        password = self.password.text()
        self.controller.run(
            lambda progress, token: self.service.encrypt_file(
                input_path,
                password,
                progress=progress,
                cancel_token=token,
            )
        )

    def decrypt(self) -> None:
        if not self._validate_ready():
            return
        input_path = self.selected_file
        assert input_path is not None
        password = self.password.text()
        self._pending_legacy_request = (input_path, password)
        started = self.controller.run(
            lambda progress, token: self.service.decrypt_file(
                input_path,
                password,
                progress=progress,
                cancel_token=token,
                allow_legacy=False,
            )
        )
        if not started:
            self._pending_legacy_request = None

    def has_running_task(self) -> bool:
        return self.controller.busy

    def cancel(self) -> None:
        self.controller.cancel()

    def wait_for_task(self, timeout_ms: int = 30_000) -> bool:
        return self.controller.wait_for_finished(timeout_ms)

    def focus_initial(self) -> None:
        self.picker.select_button.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _validate_ready(self) -> bool:
        if not self.selected_file:
            self.alert.show_error(self.i18n, ValidationError("No file selected.", code="file.not_found"))
            self.picker.select_button.setFocus()
            return False
        if not self.password.text():
            self.alert.show_error(
                self.i18n,
                ValidationError("Password is required.", code="validation.password_required"),
            )
            self.password.edit.setFocus()
            return False
        return True

    def _on_success(self, result: FileProcessResult) -> None:
        self._pending_legacy_request = None
        self.progress.reset()
        lines = [
            self.i18n.t("result.success"),
            self.i18n.t("result.output", path=str(result.output_path)),
            self.i18n.t(
                "result.size_change",
                before=format_size(result.original_size),
                after=format_size(result.output_size),
            ),
            self.i18n.t("result.format", format=result.format_name),
        ]
        if result.compatibility_warning:
            lines.append(self.i18n.t(f"warning.{result.compatibility_warning}"))
        self.result.set_result("\n".join(lines), result.output_path)
        self.status_message.emit(self.i18n.t("status.done"), 3000)
        self.result.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.progress.reset()
        if isinstance(exc, AppError) and exc.code == "legacy.file_recovery_required":
            request = self._pending_legacy_request
            self._pending_legacy_request = None
            if request is not None:
                if confirm_legacy_file_recovery(self, self.i18n, request[0]):
                    input_path, password = request
                    self.alert.clear()
                    self.controller.run(
                        lambda progress, token: self.service.recover_legacy_file(
                            input_path,
                            password,
                            progress=progress,
                            cancel_token=token,
                        )
                    )
                    return
                self.alert.show_message(self.i18n.t("recovery.file_declined"))
                self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
                self.status_message.emit(self.i18n.t("status.recovery_declined"), 5000)
                return
        self._pending_legacy_request = None
        self.alert.show_error(self.i18n, exc)
        self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
        self.status_message.emit(self.i18n.t("status.failed"), 5000)
        self.error.emit(exc, diagnostic)

    def _on_cancelled(self) -> None:
        self._pending_legacy_request = None
        self.progress.reset()
        self.status_message.emit(self.i18n.t("status.cancelled"), 3000)

    def _on_progress(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            self.progress.set_event(event)
            self.status_message.emit(self.i18n.t(f"status.{event.stage}"), 1200)

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.run_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        self.mode.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.confirm_password.setEnabled(not busy and self.mode.current == "encrypt")
        self.picker.set_input_enabled(not busy)
        self.progress.set_state(state)

    def _on_mode_changed(self, value: str) -> None:
        is_encrypt = value == "encrypt"
        self.confirm_password.setVisible(is_encrypt)
        self.confirm_password.setEnabled(not self.controller.busy and is_encrypt)
        self.legacy_note.setVisible(not is_encrypt)
        self.run_button.setText(self.i18n.t("action.encrypt" if is_encrypt else "action.decrypt"))
        self.run_button.setAccessibleName(self.run_button.text())
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        path = self.selected_file
        output_dir = self.settings.default_output_dir or (str(path.parent) if path else "")
        self.output_dir.setText(output_dir or self.i18n.t("file.output_same_folder"))
        self.overwrite_warning.setVisible(self.settings.overwrite_outputs)
        if path is None:
            self.output_preview.setText(self.i18n.t("file.output_preview_empty"))
            self.picker.clear()
            return
        output_path = self._preview_output(path)
        self.output_preview.setText(self.i18n.t("file.output_preview", path=output_path))
        self.picker.set_file(path, self._file_labels(path))

    def _file_labels(self, path: Path) -> dict[str, str]:
        return {
            self.i18n.t("file.path_label"): str(path),
            self.i18n.t("file.size_label"): format_size(safe_stat_size(path)),
            self.i18n.t("file.type_label"): path.suffix or self.i18n.t("file.type_unknown"),
        }

    def _preview_output(self, path: Path, *, encrypt: bool | None = None) -> str:
        try:
            output_dir = Path(self.settings.default_output_dir) if self.settings.default_output_dir else None
            active_encrypt = self.mode.current == "encrypt" if encrypt is None else encrypt
            if active_encrypt:
                return str(encrypted_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
            return str(decrypted_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
        except Exception:
            return self.i18n.t("file.output_unavailable")
