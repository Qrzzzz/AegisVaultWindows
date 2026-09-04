"""Minimal Base64 text and file workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.models import FileProcessResult, ProgressEvent, TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import base64_decoded_output_path, base64_encoded_output_path
from aegisvault.settings.models import AppSettings
from aegisvault.ui.components.file_picker import FilePicker
from aegisvault.ui.components.inline_alert import InlineAlert
from aegisvault.ui.components.mode_combo import ModeCombo
from aegisvault.ui.components.output_preview import OutputPreview
from aegisvault.ui.components.result_summary import ResultSummary
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
        self.setObjectName("Base64Page")
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

        self.kind = ModeCombo(
            [(self.i18n.t("base64.kind.text"), "text"), (self.i18n.t("base64.kind.file"), "file")],
            "text",
            self.i18n.t("access.input_kind"),
        )
        self.kind.changed.connect(self._on_kind_changed)
        self.mode = ModeCombo(
            [(self.i18n.t("action.encode"), "encode"), (self.i18n.t("action.decode"), "decode")],
            "encode",
            self.i18n.t("access.operation_mode"),
        )
        self.file_mode = self.mode
        self.mode.changed.connect(self._on_mode_changed)
        self.kind_label = QLabel()
        self.kind_label.setBuddy(self.kind)
        self.mode_label = QLabel()
        self.mode_label.setBuddy(self.mode)

        self.input = QPlainTextEdit()
        self.input.setMinimumHeight(90)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.relaxed_decode = QCheckBox()
        self.text_input = QWidget()
        text_layout = QVBoxLayout(self.text_input)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self.input)
        text_layout.addWidget(self.relaxed_decode)

        self.picker = FilePicker("", "", "")
        self.picker.file_selected.connect(self.set_file)
        self.output_preview = QLabel()
        self.output_preview.setWordWrap(True)
        self.output_preview.setTextFormat(Qt.TextFormat.PlainText)
        self.output_preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.alert = InlineAlert()
        self.run_button = QPushButton()
        self.run_button.clicked.connect(self.run_current)
        self.run_file_button = self.run_button
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear_current)
        self.progress = TaskProgress(self.i18n)
        self.progress.cancel_button.clicked.connect(self.cancel)
        self.output = OutputPreview("", "", "")
        self.output.use_as_input_requested.connect(self.use_result_as_input)
        self.result = ResultSummary("", "")
        self.result.reveal_requested.connect(self.reveal_requested.emit)

        scroll, layout = scroll_page()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.addWidget(scroll, 1)
        choices = QHBoxLayout()
        choices.addWidget(self.kind_label)
        choices.addWidget(self.kind)
        choices.addSpacing(12)
        choices.addWidget(self.mode_label)
        choices.addWidget(self.mode)
        choices.addStretch(1)
        layout.addLayout(choices)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        layout.addWidget(self.text_input, 1)
        layout.addWidget(self.picker)
        layout.addWidget(self.output_preview)
        layout.addWidget(self.output, 1)
        layout.addWidget(self.result)
        self.file_spacer = QWidget()
        layout.addWidget(self.file_spacer, 1)
        actions = QHBoxLayout()
        actions.addWidget(self.clear_button)
        actions.addStretch(1)
        actions.addWidget(self.run_button)
        outer.addLayout(actions)
        outer.addWidget(self.progress)
        outer.addWidget(self.alert)

        self.run_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.run_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.run_shortcut.activated.connect(self.run_current)
        self.cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.cancel_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.cancel_shortcut.activated.connect(self.cancel)
        self.retranslate_ui()
        self._on_kind_changed("text")
        self._on_mode_changed("encode")

    def set_service(self, service: CryptoService) -> None:
        self.service = service
        self._refresh_preview()

    def retranslate_ui(self) -> None:
        self.kind.set_labels(
            [(self.i18n.t("base64.kind.text"), "text"), (self.i18n.t("base64.kind.file"), "file")],
            self.i18n.t("access.input_kind"),
        )
        self.mode.set_labels(
            [(self.i18n.t("action.encode"), "encode"), (self.i18n.t("action.decode"), "decode")],
            self.i18n.t("access.operation_mode"),
        )
        self.note.setText(self.i18n.t("base64.warning_short"))
        self.kind_label.setText(self.i18n.t("base64.input_kind"))
        self.mode_label.setText(self.i18n.t("base64.operation"))
        self.input.setPlaceholderText(self.i18n.t("base64.input.placeholder"))
        self.input.setAccessibleName(self.i18n.t("access.base64_text_input"))
        self.relaxed_decode.setText(self.i18n.t("base64.relaxed_decode"))
        self.relaxed_decode.setAccessibleName(self.i18n.t("base64.relaxed_decode"))
        self.picker.set_texts(
            self.i18n.t("action.select_file"),
            self.i18n.t("file.no_file"),
            self.i18n.t("base64.file_hint"),
        )
        self.clear_button.setText(self.i18n.t("action.clear_workspace"))
        self.clear_button.setAccessibleName(self.i18n.t("action.clear_workspace"))
        self.output.set_texts(
            self.i18n.t("action.copy"),
            self.i18n.t("action.clear_result"),
            self.i18n.t("action.use_as_input"),
            self.i18n.t("base64.output.placeholder"),
        )
        self.output.set_accessible_name(self.i18n.t("access.base64_text_output"))
        self.result.set_texts(self.i18n.t("action.open_output"), self.i18n.t("action.clear_result"))
        self.progress.retranslate_ui()
        self._on_kind_changed(self.kind.current)
        self._on_mode_changed(self.mode.current)
        self._refresh_preview()

    def run_current(self) -> None:
        if self.controller.busy:
            return
        self.alert.clear()
        if self.kind.current == "text":
            text = self.input.toPlainText()
            if self.mode.current == "encode":
                self.controller.run(lambda _progress, _token: self.service.base64_encode_text(text))
            else:
                relaxed = self.relaxed_decode.isChecked()
                self.controller.run(
                    lambda _progress, _token: self.service.base64_decode_text(
                        text,
                        strict=not relaxed,
                        ignore_ascii_whitespace=relaxed,
                    )
                )
            return
        if not self._validate_file():
            return
        input_path = self.selected_file
        assert input_path is not None
        if self.mode.current == "encode":
            self.controller.run(
                lambda progress, token: self.service.base64_encode_file(
                    input_path,
                    progress=progress,
                    cancel_token=token,
                )
            )
        else:
            self.controller.run(
                lambda progress, token: self.service.base64_decode_file(
                    input_path,
                    progress=progress,
                    cancel_token=token,
                )
            )

    def encode_text(self) -> None:
        self.kind.set_current("text")
        self.mode.set_current("encode")
        self.run_current()

    def decode_text(self) -> None:
        self.kind.set_current("text")
        self.mode.set_current("decode")
        self.run_current()

    def encode_file(self) -> None:
        self.kind.set_current("file")
        self.mode.set_current("encode")
        self.run_current()

    def decode_file(self) -> None:
        self.kind.set_current("file")
        self.mode.set_current("decode")
        self.run_current()

    def set_file(self, path: object) -> bool:
        if self.controller.busy or not isinstance(path, (str, Path)):
            return False
        file_path = Path(path)
        if not file_path.is_file():
            return False
        self.selected_file = file_path
        self.file_selected.emit(file_path)
        self.alert.clear()
        self._refresh_preview()
        return True

    def clear_current(self) -> None:
        if self.controller.busy:
            return
        self.alert.clear()
        if self.kind.current == "text":
            self.input.clear()
            self.output.clear()
            self.input.setFocus()
        else:
            self.selected_file = None
            self.picker.clear()
            self.result.clear()
            self._refresh_preview()
            self.picker.select_button.setFocus()

    def clear_text(self) -> None:
        self.kind.set_current("text")
        self.clear_current()

    def use_result_as_input(self) -> None:
        text = self.output.text()
        if not text or self.controller.busy:
            return
        self.input.setPlainText(text)
        self.output.clear()
        self.kind.set_current("text")
        next_mode = "decode" if self.mode.current == "encode" else "encode"
        self.mode.set_current(next_mode)
        self.input.setFocus()

    def swap_text(self) -> None:
        self.use_result_as_input()

    def run_file(self) -> None:
        self.kind.set_current("file")
        self.run_current()

    def has_running_task(self) -> bool:
        return self.controller.busy

    def cancel(self) -> None:
        self.controller.cancel()

    def wait_for_task(self, timeout_ms: int = 30_000) -> bool:
        return self.controller.wait_for_finished(timeout_ms)

    def focus_initial(self) -> None:
        target = self.input if self.kind.current == "text" else self.picker.select_button
        target.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _validate_file(self) -> bool:
        if not self.selected_file:
            self.alert.show_error(self.i18n, ValidationError("No file selected.", code="file.not_found"))
            self.picker.select_button.setFocus()
            return False
        return True

    def _on_success(self, result: object) -> None:
        self.progress.reset()
        if isinstance(result, str):
            self.output.set_text(result)
            self.output.editor.setFocus()
        elif isinstance(result, FileProcessResult):
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
            self.result.set_result("\n".join(lines), result.output_path)
            self.result.setFocus(Qt.FocusReason.OtherFocusReason)
        self.status_message.emit(self.i18n.t("status.done"), 3000)

    def _on_failed(self, exc: object, diagnostic: str) -> None:
        self.progress.reset()
        self.alert.show_error(self.i18n, exc)
        self.alert.setFocus(Qt.FocusReason.OtherFocusReason)
        self.status_message.emit(self.i18n.t("status.failed"), 5000)
        self.error.emit(exc, diagnostic)

    def _on_cancelled(self) -> None:
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
        self.kind.setEnabled(not busy)
        self.input.setReadOnly(busy)
        self.relaxed_decode.setEnabled(not busy)
        self.picker.set_input_enabled(not busy)
        self.progress.set_state(state)

    def _on_kind_changed(self, value: str) -> None:
        is_text = value == "text"
        self.text_input.setVisible(is_text)
        self.picker.setVisible(not is_text)
        self.file_spacer.setVisible(not is_text)
        self.output.setVisible(is_text and bool(self.output.text()))
        self.result.setVisible(not is_text and bool(self.result.label.text()))
        self.relaxed_decode.setVisible(is_text and self.mode.current == "decode")
        self._on_mode_changed(self.mode.current)

    def _on_mode_changed(self, value: str) -> None:
        is_encode = value == "encode"
        is_file = self.kind.current == "file"
        key = (
            "action.encode_file"
            if is_file and is_encode
            else "action.decode_file"
            if is_file
            else "action.encode"
            if is_encode
            else "action.decode"
        )
        self.run_button.setText(self.i18n.t(key))
        self.run_button.setAccessibleName(self.run_button.text())
        self.relaxed_decode.setVisible(not is_file and not is_encode)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        self.output_preview.setVisible(self.kind.current == "file" and self.selected_file is not None)
        if self.selected_file:
            self.picker.set_file(self.selected_file, self._file_labels(self.selected_file))
            self.output_preview.setText(
                self.i18n.t(
                    "file.output_preview",
                    path=self._preview_output(self.selected_file, encode=self.mode.current == "encode"),
                )
            )

    def _file_labels(self, path: Path) -> dict[str, str]:
        return {
            self.i18n.t("file.path_label"): str(path),
            self.i18n.t("file.size_label"): format_size(safe_stat_size(path)),
            self.i18n.t("file.type_label"): path.suffix or self.i18n.t("file.type_unknown"),
        }

    def _preview_output(self, path: Path, *, encode: bool) -> str:
        try:
            output_dir = Path(self.settings.default_output_dir) if self.settings.default_output_dir else None
            if encode:
                return str(base64_encoded_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
            return str(base64_decoded_output_path(path, output_dir, overwrite=self.settings.overwrite_outputs))
        except Exception:
            return self.i18n.t("file.output_unavailable")
