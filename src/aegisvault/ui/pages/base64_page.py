"""Base64 encoding workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.models import FileProcessResult, ProgressEvent, TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import base64_decoded_output_path, base64_encoded_output_path
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.action_bar import ActionBar
from aegisvault.ui.components.card import Card
from aegisvault.ui.components.file_picker_card import FilePickerCard
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.components.output_preview import OutputPreview
from aegisvault.ui.components.result_summary import ResultSummary
from aegisvault.ui.components.segmented_control import SegmentedControl
from aegisvault.ui.components.task_progress import TaskProgress
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import format_size, safe_stat_size, scroll_page


class Base64Page(QWidget):
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
        self.controller.succeeded.connect(self._on_file_success)
        self.controller.failed.connect(self._on_failed)
        self.controller.cancelled.connect(self._on_cancelled)
        self.controller.state_changed.connect(self._on_state)

        self.alert = InlineAlert()
        self.file_alert = InlineAlert()
        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        note = Card("Base64 is encoding, not encryption")
        note.content_layout.addWidget(self.alert)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_text_tab(), "Text Base64")
        self.tabs.addTab(self._build_file_tab(), "File Base64")
        layout.addWidget(note)
        layout.addWidget(self.tabs)
        layout.addStretch(1)

    def _build_text_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(self.i18n.t("base64.input.placeholder"))
        self.output = OutputPreview(self.i18n.t("action.copy"), self.i18n.t("action.clear"), "Swap")
        self.output.swap_requested.connect(self.swap_text)
        self.relaxed_decode = QCheckBox("Ignore ASCII whitespace while decoding")
        encode = QPushButton(self.i18n.t("action.encode"))
        encode.setObjectName("Primary")
        decode = QPushButton(self.i18n.t("action.decode"))
        clear = QPushButton(self.i18n.t("action.clear"))
        encode.clicked.connect(self.encode_text)
        decode.clicked.connect(self.decode_text)
        clear.clicked.connect(self.clear_text)
        input_card = Card(self.i18n.t("field.input"))
        input_card.content_layout.addWidget(self.input)
        output_card = Card(self.i18n.t("field.output"))
        output_card.content_layout.addWidget(self.output)
        layout.addWidget(input_card)
        layout.addWidget(self.relaxed_decode)
        layout.addWidget(ActionBar(clear, decode, encode))
        layout.addWidget(output_card)
        return tab

    def _build_file_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.file_mode = SegmentedControl(
            [(self.i18n.t("action.encode"), "encode"), (self.i18n.t("action.decode"), "decode")],
            "encode",
        )
        self.file_mode.changed.connect(lambda _mode: self._refresh_preview())
        self.picker = FilePickerCard(self.i18n.t("action.select_file"), self.i18n.t("file.no_file"), self.i18n.t("base64.file_hint"))
        self.picker.file_selected.connect(self.set_file)
        self.progress = TaskProgress(self.i18n.t("action.cancel"))
        self.progress.cancel_button.clicked.connect(self.controller.cancel)
        self.run_file_button = QPushButton(self.i18n.t("action.encode_file"))
        self.run_file_button.setObjectName("Primary")
        self.run_file_button.clicked.connect(self.run_file)
        self.result = ResultSummary(self.i18n.t("action.open_output"), self.i18n.t("action.clear"))
        self.result.reveal_requested.connect(self.reveal_requested.emit)
        file_card = Card("File Base64")
        file_card.content_layout.addWidget(self.file_alert)
        file_card.content_layout.addWidget(self.file_mode)
        file_card.content_layout.addWidget(self.picker)
        file_card.content_layout.addWidget(self.progress)
        file_card.content_layout.addWidget(ActionBar(self.run_file_button))
        file_card.content_layout.addWidget(self.result)
        layout.addWidget(file_card)
        return tab

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

    def encode_text(self) -> None:
        self.alert.clear()
        self.output.set_text(self.service.base64_encode_text(self.input.toPlainText()))

    def decode_text(self) -> None:
        self.alert.clear()
        try:
            self.output.set_text(
                self.service.base64_decode_text(
                    self.input.toPlainText(),
                    strict=not self.relaxed_decode.isChecked(),
                    ignore_ascii_whitespace=self.relaxed_decode.isChecked(),
                )
            )
        except Exception as exc:
            self.alert.show_error(self.i18n, exc)

    def clear_text(self) -> None:
        self.alert.clear()
        self.input.clear()
        self.output.clear()

    def swap_text(self) -> None:
        if self.output.text():
            self.input.setPlainText(self.output.text())
            self.output.clear()

    def run_file(self) -> None:
        self.file_alert.clear()
        if self.file_mode.current == "encode":
            self.encode_file()
        else:
            self.decode_file()

    def encode_file(self) -> None:
        if not self._validate_file():
            return
        input_path = self.selected_file
        assert input_path is not None
        self.controller.run(lambda progress, token: self.service.base64_encode_file(input_path, progress=progress, cancel_token=token))

    def decode_file(self) -> None:
        if not self._validate_file():
            return
        input_path = self.selected_file
        assert input_path is not None
        self.controller.run(lambda progress, token: self.service.base64_decode_file(input_path, progress=progress, cancel_token=token))

    def has_running_task(self) -> bool:
        return self.controller.busy

    def cancel(self) -> None:
        self.controller.cancel()

    def _validate_file(self) -> bool:
        if not self.selected_file:
            self.file_alert.show_error(self.i18n, ValidationError("No file selected.", code="file.not_found"))
            return False
        return True

    def _on_file_success(self, result: FileProcessResult) -> None:
        lines = [
            self.i18n.t("result.success"),
            self.i18n.t("result.output", path=str(result.output_path)),
            self.i18n.t("result.size_change", before=format_size(result.original_size), after=format_size(result.output_size)),
            self.i18n.t("result.format", format=result.format_name),
        ]
        self.result.set_result("\n".join(lines), result.output_path)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.file_alert.show_error(self.i18n, exc)
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
        self.run_file_button.setEnabled(not busy)
        self.file_mode.setEnabled(not busy)
        self.picker.select_button.setEnabled(not busy)
        self.progress.set_running(busy)

    def _refresh_preview(self) -> None:
        self.run_file_button.setText(self.i18n.t("action.encode_file" if self.file_mode.current == "encode" else "action.decode_file"))
        if self.selected_file:
            self.picker.set_file(self.selected_file, self._file_labels(self.selected_file))

    def _file_labels(self, path: Path) -> dict[str, str]:
        return {
            self.i18n.t("file.path"): str(path),
            self.i18n.t("file.size_label"): format_size(safe_stat_size(path)),
            self.i18n.t("file.type_label"): path.suffix or self.i18n.t("file.type_unknown"),
            "Encode output": self._preview_output(path, encode=True),
            "Decode output": self._preview_output(path, encode=False),
        }

    def _preview_output(self, path: Path, *, encode: bool) -> str:
        try:
            output_dir = Path(self.settings.default_output_dir) if self.settings.default_output_dir else None
            if encode:
                return str(base64_encoded_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
            return str(base64_decoded_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
        except Exception:
            return self.i18n.t("file.output_unavailable")
