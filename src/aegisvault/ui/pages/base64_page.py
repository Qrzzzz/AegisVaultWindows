"""Minimal Base64 text and file workspace."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from aegisvault.ui.components.mode_switch import ModeSwitch
from aegisvault.ui.components.output_preview import OutputPreview
from aegisvault.ui.components.result_summary import ResultSummary
from aegisvault.ui.components.task_progress import TaskProgress
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.pages.common import (
    AdaptiveRow,
    PageHeader,
    WorkspacePage,
    action_row,
    form_group,
    format_size,
    input_group,
    result_area,
    safe_stat_size,
    scroll_page,
    tab_order,
)


class Base64Page(WorkspacePage):
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
        self._last_result: FileProcessResult | None = None
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
        self.mode = ModeSwitch(
            [(self.i18n.t("action.encode"), "encode"), (self.i18n.t("action.decode"), "decode")],
            "encode",
            self.i18n.t("access.operation_mode"),
        )
        self.file_mode = self.mode
        self.mode.changed.connect(self._on_mode_changed)
        self.kind_label = QLabel()
        self.kind_label.setBuddy(self.kind)

        self.input = QPlainTextEdit()
        self.input.setTabChangesFocus(True)
        self.input.setMinimumHeight(90)
        self.input.setMaximumHeight(210)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.relaxed_decode = QCheckBox()
        self.text_input = QWidget()
        text_layout = QVBoxLayout(self.text_input)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(self.input)
        text_layout.addWidget(self.relaxed_decode)

        self.picker = FilePicker("", "", "")
        self.picker.file_selected.connect(self.set_file)
        self.output_dir = QLineEdit()
        self.output_dir.setReadOnly(True)
        self.output_dir.setProperty("outputPath", True)
        self.output_dir_label = QLabel()
        self.output_dir_label.setBuddy(self.output_dir)
        self.output_preview = QLineEdit()
        self.output_preview.setReadOnly(True)
        self.output_preview.setProperty("outputPath", True)
        self.output_preview_label = QLabel()
        self.output_preview_label.setBuddy(self.output_preview)
        self.overwrite_warning = QLabel()
        self.overwrite_warning.setWordWrap(True)
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

        self.input_scroll, layout = scroll_page()
        self.outer = outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(20)
        outer.addWidget(self.input_scroll, 1)
        self.header = PageHeader()
        layout.addWidget(self.header)
        input_kind = QWidget()
        choices = QHBoxLayout(input_kind)
        choices.setContentsMargins(0, 0, 0, 0)
        choices.addStretch(1)
        choices.addWidget(self.kind_label)
        choices.addWidget(self.kind)
        layout.addWidget(AdaptiveRow(self.mode, input_kind))
        self.note = QLabel()
        self.note.setProperty("muted", True)
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.input_group = input_group(self.text_input)
        self.input_group.title.setBuddy(self.input)
        self.file_group = input_group(self.picker)
        layout.addWidget(self.input_group, 1)
        layout.addWidget(self.file_group)
        self.output_group, self.output_form = form_group()
        self.output_form.addRow(self.output_dir_label, self.output_dir)
        self.output_form.addRow(self.output_preview_label, self.output_preview)
        self.output_form.addRow(self.overwrite_warning)
        layout.addWidget(self.output_group)
        outer.addLayout(action_row(self.run_button, self.clear_button))
        outer.addWidget(self.progress)
        outer.addWidget(self.alert)
        self.result_scroll = result_area(self.output, self.result)
        outer.addWidget(self.result_scroll, 1)
        self.file_spacer = QWidget()
        outer.addWidget(self.file_spacer, 1)
        self.output.content_changed.connect(self._sync_result_area)
        self.result.content_changed.connect(self._sync_result_area)
        tab_order(
            self.kind, self.mode, self.input, self.relaxed_decode, self.picker.select_button,
            self.picker.path_edit, self.output_dir, self.output_preview, self.run_button,
            self.clear_button, self.output.editor, self.output.copy_button,
            self.output.clear_button, self.output.use_as_input_button,
            self.result.open_button, self.result.clear_button,
        )

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
        if self._last_result is not None and self.result.output_path is not None:
            self._render_file_result(self._last_result)

    def retranslate_ui(self) -> None:
        self.header.set_texts(self.i18n.t("base64.title"), self.i18n.t("base64.description"))
        self.kind.set_labels(
            [(self.i18n.t("base64.kind.text"), "text"), (self.i18n.t("base64.kind.file"), "file")],
            self.i18n.t("access.input_kind"),
        )
        self.mode.set_labels(
            [(self.i18n.t("action.encode"), "encode"), (self.i18n.t("action.decode"), "decode")],
            self.i18n.t("access.operation_mode"),
        )
        self.note.setText(self.i18n.t("base64.warning_short"))
        self.input_group.setTitle(self.i18n.t("flow.input"))
        self.file_group.setTitle("")
        self.output_group.setTitle("")
        self.output.setTitle(self.i18n.t("flow.result"))
        self.result.setTitle(self.i18n.t("flow.result"))
        self.output_dir_label.setText(self.i18n.t("field.output_dir"))
        self.output_dir.setAccessibleName(self.output_dir_label.text())
        self.output_preview_label.setText(self.i18n.t("file.output_name"))
        self.output_preview.setAccessibleName(self.output_preview_label.text())
        self.overwrite_warning.setText(self.i18n.t("warning.overwrite_enabled"))
        self.kind_label.setText(self.i18n.t("base64.input_kind"))
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
            self._last_result = result
            self._render_file_result(result)
            self.result.setFocus(Qt.FocusReason.OtherFocusReason)
        self.status_message.emit(self.i18n.t("status.done"), 3000)

    def _render_file_result(self, result: FileProcessResult) -> None:
        lines = [
            self.i18n.t("result.success"),
            self.i18n.t("result.output", path=str(result.output_path)),
            self.i18n.t("result.size_change", before=format_size(result.original_size), after=format_size(result.output_size)),
            self.i18n.t("result.format", format=result.format_name),
        ]
        self.result.set_result("\n".join(lines), result.output_path)
        self.result.setVisible(self.kind.current == "file")

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
        self.output.set_busy(busy)
        self.output.setVisible(self.kind.current == "text" and bool(self.output.text()))
        self.result.clear_button.setEnabled(not busy)
        self.progress.set_state(state)

    def _on_kind_changed(self, value: str) -> None:
        is_text = value == "text"
        self.input_group.setVisible(is_text)
        self.file_group.setVisible(not is_text)
        self.output_group.setVisible(not is_text)
        self.text_input.setVisible(is_text)
        self.picker.setVisible(not is_text)
        self.file_spacer.setVisible(True)
        self.output.setVisible(is_text and bool(self.output.text()))
        self.result.setVisible(not is_text and bool(self.result.label.text()))
        self._sync_result_area()
        self.outer.setStretchFactor(self.input_scroll, 0)
        self.outer.setStretchFactor(self.result_scroll, 0)
        self.relaxed_decode.setVisible(is_text and self.mode.current == "decode")
        self._on_mode_changed(self.mode.current)

    def _sync_result_area(self) -> None:
        is_text = self.kind.current == "text"
        self.result_scroll.setVisible(bool(self.output.text()) if is_text else bool(self.result.label.text()))
        self.update_editor_height()

    def _on_mode_changed(self, value: str) -> None:
        is_encode = value == "encode"
        is_file = self.kind.current == "file"
        self.input_group.setTitle(self.i18n.t("modern.input.base64" if not is_encode else "modern.input.encode"))
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
        path = self.selected_file
        output_dir = self.settings.default_output_dir or (str(path.parent) if path else "")
        self.output_dir.setText(output_dir or self.i18n.t("file.output_same_folder"))
        self.output_dir.setToolTip(self.output_dir.text())
        self.output_form.setRowVisible(self.output_preview, path is not None)
        self.overwrite_warning.setVisible(self.settings.overwrite_outputs)
        if self.selected_file:
            self.picker.set_file(self.selected_file, self._file_labels(self.selected_file))
            output_path = self._preview_output(self.selected_file, encode=self.mode.current == "encode")
            self.output_preview.setText(output_path)
            self.output_preview.setToolTip(output_path)

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
