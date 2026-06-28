"""File encryption workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from aegisvault.core.exceptions import ValidationError
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
from aegisvault.ui.design import spacing
from aegisvault.ui.pages.common import format_size, safe_stat_size, scroll_page


class FilePage(QWidget):
    error = Signal(object, str)
    status_message = Signal(str, int)
    reveal_requested = Signal(object)
    file_selected = Signal(object)

    def __init__(self, translator: Translator, settings: AppSettings, service: CryptoService) -> None:
        super().__init__()
        self.i18n = translator
        self.settings = settings
        self.service = service
        self.selected_file: Path | None = None
        self.controller = TaskController(self)
        self.controller.progress_changed.connect(self._on_progress)
        self.controller.succeeded.connect(self._on_success)
        self.controller.failed.connect(self._on_failed)
        self.controller.cancelled.connect(self._on_cancelled)
        self.controller.state_changed.connect(self._on_state)

        self.alert = InlineAlert()
        self.picker = FilePickerCard(self.i18n.t("action.select_file"), self.i18n.t("file.no_file"), self.i18n.t("file.drop_hint"))
        self.picker.file_selected.connect(self.set_file)
        self.mode = SegmentedControl(
            [(self.i18n.t("action.encrypt"), "encrypt"), (self.i18n.t("action.decrypt"), "decrypt")],
            "encrypt",
        )
        self.mode.changed.connect(lambda _mode: self._refresh_preview())
        self.password = PasswordInput(
            self.i18n.t("field.password"),
            self.i18n.t("field.password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.output_dir = QLineEdit()
        self.output_dir.setReadOnly(True)
        self.output_preview = QLabel("")
        self.output_preview.setObjectName("Muted")
        self.output_preview.setWordWrap(True)
        self.run_button = QPushButton("Run")
        self.run_button.setObjectName("Primary")
        self.run_button.clicked.connect(self.run_current)
        self.progress = TaskProgress(self.i18n.t("action.cancel"))
        self.progress.cancel_button.clicked.connect(self.controller.cancel)
        self.result = ResultSummary(self.i18n.t("action.open_output"), self.i18n.t("action.clear"))
        self.result.reveal_requested.connect(self.reveal_requested.emit)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        grid = QGridLayout()
        grid.setHorizontalSpacing(spacing.LG)
        grid.setVerticalSpacing(spacing.LG)
        step1 = Card("Step 1: Select file")
        step1.content_layout.addWidget(self.picker)
        step2 = Card("Step 2: Choose operation")
        step2.content_layout.addWidget(self.mode)
        step3 = Card("Step 3: Password and output")
        step3.content_layout.addWidget(self.password)
        step3.content_layout.addWidget(FormRow(self.i18n.t("field.output_dir"), self.output_dir))
        step3.content_layout.addWidget(self.output_preview)
        step3.content_layout.addWidget(self.alert)
        step4 = Card("Step 4: Execute and review")
        step4.content_layout.addWidget(self.progress)
        step4.content_layout.addWidget(ActionBar(self.run_button))
        step4.content_layout.addWidget(self.result)
        grid.addWidget(step1, 0, 0)
        grid.addWidget(step2, 0, 1)
        grid.addWidget(step3, 1, 0)
        grid.addWidget(step4, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        self._refresh_preview()

    def set_service(self, service: CryptoService) -> None:
        self.service = service
        self._refresh_preview()

    def set_file(self, path: object) -> None:
        if not isinstance(path, (str, Path)):
            return
        file_path = Path(path)
        if not file_path.is_file():
            return
        self.selected_file = file_path
        self.file_selected.emit(file_path)
        self.picker.set_file(file_path, self._file_labels(file_path))
        self.result.clear()
        self._refresh_preview()

    def run_current(self) -> None:
        self.alert.clear()
        if self.mode.current == "encrypt":
            self.encrypt()
        else:
            self.decrypt()

    def encrypt(self) -> None:
        if not self._validate_ready():
            return
        input_path = self.selected_file
        assert input_path is not None
        self.controller.run(lambda progress, token: self.service.encrypt_file(input_path, self.password.text(), progress=progress, cancel_token=token))

    def decrypt(self) -> None:
        if not self._validate_ready():
            return
        input_path = self.selected_file
        assert input_path is not None
        self.controller.run(lambda progress, token: self.service.decrypt_file(input_path, self.password.text(), progress=progress, cancel_token=token))

    def has_running_task(self) -> bool:
        return self.controller.busy

    def cancel(self) -> None:
        self.controller.cancel()

    def _validate_ready(self) -> bool:
        if not self.selected_file:
            self.alert.show_error(self.i18n, ValidationError("No file selected.", code="file.not_found"))
            return False
        if not self.password.text():
            self.alert.show_error(self.i18n, ValidationError("Password is required.", code="validation.password_required"))
            return False
        return True

    def _on_success(self, result: FileProcessResult) -> None:
        lines = [
            self.i18n.t("result.success"),
            self.i18n.t("result.output", path=str(result.output_path)),
            self.i18n.t("result.size_change", before=format_size(result.original_size), after=format_size(result.output_size)),
            self.i18n.t("result.format", format=result.format_name),
        ]
        if result.compatibility_warning:
            lines.append(self.i18n.t(f"warning.{result.compatibility_warning}"))
        self.result.set_result("\n".join(lines), result.output_path)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.alert.show_error(self.i18n, exc)
        self.error.emit(exc, diagnostic)

    def _on_cancelled(self) -> None:
        self.progress.reset()
        self.result.set_result(self.i18n.t("status.cancelled"))

    def _on_progress(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            self.progress.set_event(event)
            self.status_message.emit(self.i18n.t(f"status.{event.stage}"), 1000)

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.run_button.setEnabled(not busy)
        self.mode.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.picker.select_button.setEnabled(not busy)
        self.progress.set_running(busy)
        self.run_button.setText(self.i18n.t("action.encrypt" if self.mode.current == "encrypt" else "action.decrypt"))

    def _refresh_preview(self) -> None:
        path = self.selected_file
        output_dir = self.settings.default_output_dir or (str(path.parent) if path else "")
        self.output_dir.setText(output_dir)
        self.run_button.setText(self.i18n.t("action.encrypt" if self.mode.current == "encrypt" else "action.decrypt"))
        if path is None:
            self.output_preview.setText("Output preview appears after file selection.")
            return
        self.output_preview.setText(f"Output preview: {self._preview_output(path)}")
        self.picker.set_file(path, self._file_labels(path))

    def _file_labels(self, path: Path) -> dict[str, str]:
        return {
            self.i18n.t("file.path"): str(path),
            self.i18n.t("file.size_label"): format_size(safe_stat_size(path)),
            self.i18n.t("file.type_label"): path.suffix or self.i18n.t("file.type_unknown"),
            "Encrypt output": self._preview_output(path, encrypt=True),
            "Decrypt output": self._preview_output(path, encrypt=False),
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
