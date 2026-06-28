"""File encryption workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QProgressBar, QPushButton, QWidget

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.models import FileProcessResult, ProgressEvent, TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import decrypted_output_path, encrypted_output_path
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.file_drop_zone import FileDropZone
from aegisvault.ui.components.glass_card import GlassCard
from aegisvault.ui.components.password_field import PasswordField
from aegisvault.ui.components.result_panel import ResultPanel
from aegisvault.ui.components.status_badge import StatusBadge
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import format_size, muted, page_header, safe_stat_size, scroll_page


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
        self.controller.failed.connect(self.error.emit)
        self.controller.cancelled.connect(self._on_cancelled)
        self.controller.state_changed.connect(self._on_state)

        scroll, layout = scroll_page()
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        layout.addWidget(page_header(self.i18n.t("file.title"), self.i18n.t("file.description")))
        card = GlassCard()
        self.password = PasswordField(
            self.i18n.t("field.password"),
            self.i18n.t("field.password.placeholder"),
            self.i18n.t("action.show"),
            self.i18n.t("action.hide"),
        )
        self.drop_zone = FileDropZone(self.i18n.t("action.select_file"), self.i18n.t("file.no_file"), self.i18n.t("file.drop_hint"))
        self.drop_zone.file_selected.connect(self.set_file)
        self.badge = StatusBadge(self.i18n.t("status.ready"))
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.encrypt_button = self._button("action.encrypt", primary=True)
        self.decrypt_button = self._button("action.decrypt")
        self.cancel_button = self._button("action.cancel")
        self.cancel_button.setObjectName("Danger")
        self.cancel_button.setEnabled(False)
        self.encrypt_button.clicked.connect(self.encrypt)
        self.decrypt_button.clicked.connect(self.decrypt)
        self.cancel_button.clicked.connect(self.controller.cancel)
        buttons = QHBoxLayout()
        buttons.addWidget(self.encrypt_button)
        buttons.addWidget(self.decrypt_button)
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        self.result = ResultPanel(self.i18n.t("action.copy"), self.i18n.t("action.open_output"), self.i18n.t("action.clear"))
        self.result.reveal_requested.connect(self.reveal_requested.emit)
        card.content_layout.addWidget(self.password)
        card.content_layout.addWidget(self.drop_zone)
        card.content_layout.addWidget(self.progress)
        card.content_layout.addWidget(self.badge)
        card.content_layout.addLayout(buttons)
        card.content_layout.addWidget(muted(self.i18n.t("field.output")))
        card.content_layout.addWidget(self.result)
        layout.addWidget(card)
        layout.addStretch(1)

    def set_service(self, service: CryptoService) -> None:
        self.service = service
        if self.selected_file:
            self.set_file(self.selected_file)

    def set_file(self, path: object) -> None:
        if not isinstance(path, (str, Path)):
            return
        file_path = Path(path)
        if not file_path.is_file():
            return
        self.selected_file = file_path
        self.file_selected.emit(file_path)
        self.drop_zone.set_file(file_path, self._file_labels(file_path))
        self.result.clear()

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
            self.error.emit(ValidationError("No file selected.", code="file.not_found"), "")
            return False
        if not self.password.text():
            self.error.emit(ValidationError("Password is required.", code="validation.password_required"), "")
            return False
        return True

    def _on_success(self, result: FileProcessResult) -> None:
        self.progress.setValue(100)
        lines = [
            self.i18n.t("result.success"),
            self.i18n.t("result.output", path=str(result.output_path)),
            self.i18n.t("result.size_change", before=format_size(result.original_size), after=format_size(result.output_size)),
            self.i18n.t("result.format", format=result.format_name),
        ]
        if result.compatibility_warning:
            lines.append("")
            lines.append(self.i18n.t(f"warning.{result.compatibility_warning}"))
        self.result.set_result("\n".join(lines), result.output_path)

    def _on_cancelled(self) -> None:
        self.progress.setValue(0)
        self.result.set_result(self.i18n.t("status.cancelled"))

    def _on_progress(self, event: object) -> None:
        if isinstance(event, ProgressEvent):
            self.progress.setValue(round(event.percent * 100))
            self.status_message.emit(self.i18n.t(f"status.{event.stage}"), 1000)

    def _on_state(self, state: TaskState) -> None:
        busy = state in {TaskState.RUNNING, TaskState.CANCELLING}
        self.encrypt_button.setEnabled(not busy)
        self.decrypt_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.drop_zone.select_button.setEnabled(not busy)
        self.badge.set_state(state, self.i18n.t(f"status.{state.value}"))

    def _file_labels(self, path: Path) -> dict[str, str]:
        size = safe_stat_size(path)
        output_dir = self.settings.default_output_dir or str(path.parent)
        encrypted_preview = self._preview_output(path, encrypt=True)
        decrypted_preview = self._preview_output(path, encrypt=False)
        return {
            "name": self.i18n.t("file.selected", name=path.name),
            "path": self.i18n.t("file.path", path=str(path)),
            self.i18n.t("file.size_label"): format_size(size),
            self.i18n.t("file.type_label"): path.suffix or self.i18n.t("file.type_unknown"),
            self.i18n.t("file.encrypt_output_label"): encrypted_preview,
            self.i18n.t("file.decrypt_output_label"): decrypted_preview,
            self.i18n.t("file.output_dir_label"): output_dir,
        }

    def _preview_output(self, path: Path, *, encrypt: bool) -> str:
        try:
            if encrypt:
                return encrypted_output_path(path, Path(self.settings.default_output_dir) if self.settings.default_output_dir else None, overwrite=self.settings.overwrite_outputs).name
            return decrypted_output_path(path, Path(self.settings.default_output_dir) if self.settings.default_output_dir else None, overwrite=self.settings.overwrite_outputs).name
        except Exception:
            return self.i18n.t("file.output_unavailable")

    def _button(self, key: str, *, primary: bool = False) -> QPushButton:
        button = QPushButton(self.i18n.t(key))
        if primary:
            button.setObjectName("Primary")
        return button


