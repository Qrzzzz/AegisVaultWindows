from __future__ import annotations

import os
import time
from pathlib import Path
from threading import Event

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from aegisvault.core.exceptions import FileIOError, OperationCancelled, ValidationError
from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.main_window import MainWindow
from aegisvault.ui.pages.settings_page import SettingsDialog


def _make_window(tmp_path: Path, *, language: str = "en-US") -> tuple[QApplication, MainWindow]:
    app = QApplication.instance() or QApplication([])
    settings = AppSettings(language=language)
    window = MainWindow(settings, SettingsStore(tmp_path / "settings.json"), Translator(language))
    window.show()
    app.processEvents()
    return app, window


def _wait_until(app: QApplication, predicate: object, timeout: float = 8.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if callable(predicate) and predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for Qt state")


def test_text_actions_encrypt_decrypt_and_use_result_as_input(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    page = window.text_page
    page.input.setPlainText("quiet interface")
    page.password.edit.setText("correct horse battery staple")
    page.confirm_password.edit.setText("correct horse battery staple")

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert page.output.text().startswith("AGV1.")
    assert QApplication.clipboard().text() != page.output.text()
    QTest.mouseClick(page.output.copy_button, Qt.MouseButton.LeftButton)
    assert QApplication.clipboard().text() == page.output.text()

    QTest.mouseClick(page.output.use_as_input_button, Qt.MouseButton.LeftButton)
    assert page.mode.current == "decrypt"
    assert page.output.text() == ""
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert page.output.text() == "quiet interface"
    window.close()
    app.processEvents()


def test_file_encrypt_requires_confirmation_and_reports_output(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    page = window.file_page
    source = tmp_path / "sample.txt"
    source.write_text("local file", encoding="utf-8")
    assert page.set_file(source)
    page.password.edit.setText("file password")
    page.confirm_password.edit.setText("different")

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert not page.controller.busy
    assert page.alert.label.text() == "The two passwords do not match."

    page.confirm_password.edit.setText("file password")
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert page.result.output_path is not None
    assert page.result.output_path.exists()
    assert "Completed" in page.result.label.text()
    window.close()
    app.processEvents()


# Static pre-AGV1 sample, captured before removing the retired implementation.
# Plaintext: "retired UI fixture"; password: "fixture-only-password".
# No old encryptor/decryptor/helper is retained or imported by these tests.
RETIRED_FILE_BYTES = bytes.fromhex(
    "010101010101010101010101f84f6f0381aa17e6bb7f75d3494bcbd8b50cd931fa0df510c908c8640f8851315f73"
)
RETIRED_TEXT = "AQEBAQEBAQEBAQEB+E9vA4GqF+a7f3XTSUvL2LUM2TH6DfUQyQjIZA+IUTFfcw=="


@pytest.mark.parametrize("language", ["en-US", "zh-CN"])
@pytest.mark.parametrize("suffix", [".aes", ".agv"])
def test_non_agv1_file_is_rejected_without_dialog_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str, suffix: str
) -> None:
    app, window = _make_window(tmp_path, language=language)
    window._set_page(1)
    page = window.file_page
    source = tmp_path / f"retired{suffix}"
    source.write_bytes(RETIRED_FILE_BYTES)
    page.mode.set_current("decrypt")
    assert page.set_file(source)
    page.password.edit.setText("fixture-only-password")
    before = set(tmp_path.rglob("*"))
    dialogs: list[QDialog] = []
    failures: list[object] = []
    monkeypatch.setattr(QDialog, "exec", lambda dialog: dialogs.append(dialog) or QDialog.DialogCode.Rejected)
    page.error.connect(lambda error, _detail: failures.append(error))
    app.processEvents()

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)

    assert page.controller.state == TaskState.FAILED
    assert len(failures) == 1
    assert failures[0].code == "protocol.unsupported_format"
    assert page.alert.label.text() == window.i18n.t("error.protocol.unsupported_format")
    assert dialogs == []
    assert page.result.output_path is None
    assert page.result.isHidden()
    assert set(tmp_path.rglob("*")) == before
    assert source.read_bytes() == RETIRED_FILE_BYTES
    assert not hasattr(page, "_pending_legacy_request")
    window.close()
    app.processEvents()


@pytest.mark.parametrize("language", ["en-US", "zh-CN"])
@pytest.mark.parametrize(
    ("ciphertext", "password"),
    [(RETIRED_TEXT, "fixture-only-password"), (f"AK#fixture-only-password#{RETIRED_TEXT}", "")],
    ids=["retired-base64", "ak-without-password"],
)
def test_non_agv1_text_is_rejected_without_recovery_or_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str, ciphertext: str, password: str
) -> None:
    app, window = _make_window(tmp_path, language=language)
    page = window.text_page
    page.mode.set_current("decrypt")
    page.input.setPlainText(ciphertext)
    page.password.edit.setText(password)
    dialogs: list[QDialog] = []
    failures: list[object] = []
    monkeypatch.setattr(QDialog, "exec", lambda dialog: dialogs.append(dialog) or QDialog.DialogCode.Rejected)
    page.error.connect(lambda error, _detail: failures.append(error))

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)

    assert page.controller.state == TaskState.FAILED
    assert len(failures) == 1
    assert failures[0].code == "protocol.unsupported_format"
    assert page.alert.label.text() == window.i18n.t("error.protocol.unsupported_format")
    assert page.input.toPlainText() == ciphertext
    assert page.output.text() == ""
    assert page.output.isHidden()
    assert dialogs == []
    assert not hasattr(page, "recovery_button")
    assert not list(tmp_path.iterdir())
    window.close()
    app.processEvents()


@pytest.mark.parametrize(
    ("language", "code", "expected"),
    [
        ("en-US", "file.input_changed", "input file changed"),
        ("zh-CN", "file.same_input_output", "输入路径与输出路径不能相同"),
    ],
)
def test_file_backend_safety_errors_are_shown_inline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    language: str,
    code: str,
    expected: str,
) -> None:
    app, window = _make_window(tmp_path, language=language)
    page = window.file_page
    source = tmp_path / "sample.agv"
    source.write_bytes(b"not-used")
    page.mode.set_current("decrypt")
    assert page.set_file(source)
    page.password.edit.setText("password")

    def fail(*_args: object, **_kwargs: object) -> object:
        raise FileIOError("injected backend boundary", code=code)

    monkeypatch.setattr(page.service, "decrypt_file", fail)
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert expected in page.alert.label.text()
    assert page.result.output_path is None
    window.close()
    app.processEvents()


def test_base64_has_one_primary_action_for_text_round_trip(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    window._set_page(2)
    page = window.base64_page
    page.input.setPlainText("hello")
    assert page.run_button is page.run_file_button

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert page.output.text() == "aGVsbG8="
    QTest.mouseClick(page.output.use_as_input_button, Qt.MouseButton.LeftButton)
    assert page.mode.current == "decode"
    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: not page.controller.busy)
    assert page.output.text() == "hello"
    window.close()
    app.processEvents()


def test_drag_drop_routes_file_and_running_task_blocks_replacement(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(first))])
    drop = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dropEvent(drop)
    assert drop.isAccepted()
    assert window.file_page.selected_file == first
    assert window.tabs.currentIndex() == 1

    started = Event()

    def task(_progress: object, token: object) -> None:
        started.set()
        while not token.cancelled:
            time.sleep(0.002)
        raise OperationCancelled()

    controller = window.file_page.controller
    assert controller.run(task)
    _wait_until(app, started.is_set)
    active_id = controller.active_task_id
    assert not window.file_page.set_file(second)
    assert window.file_page.selected_file == first
    assert controller.cancel()
    assert not controller.cancel()
    _wait_until(app, lambda: not controller.busy)
    retired_thread = controller._retired_threads[-1]

    assert controller.run(task)
    _wait_until(app, started.is_set)
    current_id = controller.active_task_id
    controller._finish_task(active_id or -1, retired_thread)
    assert controller.active_task_id == current_id
    assert controller.busy
    controller.cancel()
    _wait_until(app, lambda: not controller.busy)
    window.close()
    app.processEvents()


def test_native_status_timeout_restarts_and_returns_to_empty(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    status = window.statusBar()
    status.showMessage("first", 25)
    QTest.qWait(10)
    status.showMessage("second", 90)
    QTest.qWait(35)
    app.processEvents()
    assert status.currentMessage() == "second"
    QTest.qWait(80)
    app.processEvents()
    assert status.currentMessage() == ""
    window.close()
    app.processEvents()


def test_cancel_request_is_idempotent_and_suppresses_late_success() -> None:
    app = QApplication.instance() or QApplication([])
    controller = TaskController()
    started = Event()
    successes: list[object] = []
    cancellations: list[bool] = []
    controller.succeeded.connect(successes.append)
    controller.cancelled.connect(lambda: cancellations.append(True))

    def returns_after_cancel(_progress: object, token: object) -> str:
        started.set()
        while not token.cancelled:
            time.sleep(0.002)
        return "late success"

    assert controller.run(returns_after_cancel)
    _wait_until(app, started.is_set)
    assert controller.cancel()
    assert not controller.cancel()
    _wait_until(app, lambda: not controller.busy)
    assert controller.state == TaskState.CANCELLED
    assert successes == []
    assert cancellations == [True]


def test_settings_dialog_uses_real_advanced_section_and_draft_recent_files(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    settings = AppSettings(language="en-US", recent_files=["C:/private/a.txt"])
    store = SettingsStore(tmp_path / "settings.json")
    translator = Translator("en-US")
    dialog = SettingsDialog(translator, settings, store)
    assert dialog.advanced_panel.isHidden()
    QTest.mouseClick(dialog.advanced_toggle, Qt.MouseButton.LeftButton)
    assert not dialog.advanced_panel.isHidden()
    assert not hasattr(dialog, "ak")
    assert not hasattr(dialog, "ak_warning")
    assert dialog.advanced_toggle.text() == "Advanced options"
    assert dialog.overwrite_warning.text()

    QTest.mouseClick(dialog.clear_recent_button, Qt.MouseButton.LeftButton)
    dialog.reject()
    assert settings.recent_files == ["C:/private/a.txt"]

    dialog = SettingsDialog(translator, settings, store)
    dialog.advanced_toggle.setChecked(True)
    dialog.overwrite.setChecked(True)
    dialog.language_combo.setCurrentIndex(0)
    QTest.mouseClick(dialog.clear_recent_button, Qt.MouseButton.LeftButton)
    dialog.save()
    app.processEvents()
    assert settings.language == "zh-CN"
    assert settings.overwrite_outputs is True
    assert settings.recent_files == []
    assert store.load().overwrite_outputs is True


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en-US", "settings data exceeds the safe storage limit"),
        ("zh-CN", "设置数据超过安全存储上限"),
    ],
)
def test_settings_save_failure_is_localized_and_preserves_live_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    language: str,
    expected: str,
) -> None:
    app = QApplication.instance() or QApplication([])
    settings = AppSettings(language=language, theme="dark")
    store = SettingsStore(tmp_path / "settings.json")
    dialog = SettingsDialog(Translator(language), settings, store)
    dialog.remember.setChecked(False)
    errors: list[object] = []
    dialog.error.connect(lambda exc, _diagnostic: errors.append(exc))

    def fail_save(_candidate: AppSettings) -> None:
        raise ValidationError("injected settings limit", code="settings.too_large")

    monkeypatch.setattr(store, "save", fail_save)
    dialog.save()
    app.processEvents()

    assert settings.theme == "dark"
    assert settings.remember_recent_files is True
    assert expected in dialog.alert.label.text()
    assert len(errors) == 1
    assert isinstance(errors[0], ValidationError)
    assert dialog.result() != dialog.DialogCode.Accepted
    dialog.close()
    app.processEvents()


def test_close_cancels_and_waits_for_worker_terminal_state(tmp_path: Path, monkeypatch: object) -> None:
    app, window = _make_window(tmp_path)
    started = Event()

    def task(_progress: object, token: object) -> None:
        started.set()
        while not token.cancelled:
            time.sleep(0.002)
        raise OperationCancelled()

    assert window.file_page.controller.run(task)
    _wait_until(app, started.is_set)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    assert window.close()
    app.processEvents()
    assert not window.file_page.controller.busy
    assert not window.isVisible()
