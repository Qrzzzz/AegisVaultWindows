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
from PySide6.QtWidgets import QApplication, QMessageBox

from aegisvault.core.exceptions import FileIOError, OperationCancelled, ValidationError
from aegisvault.core.legacy import encrypt_legacy_bytes_for_tests
from aegisvault.core.models import TaskState
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.controllers.task_controller import TaskController
from aegisvault.ui.dialogs.legacy_recovery_dialog import LegacyRecoveryDialog
from aegisvault.ui.main_window import MainWindow
from aegisvault.ui.pages import file_page as file_page_module
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


def test_file_legacy_recovery_decline_never_invokes_compatibility_decryptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, window = _make_window(tmp_path)
    page = window.file_page
    source = tmp_path / "legacy.aes"
    source.write_bytes(encrypt_legacy_bytes_for_tests("迁移内容".encode(), "legacy-pass"))
    page.mode.set_current("decrypt")
    assert page.set_file(source)
    page.password.edit.setText("legacy-pass")

    strict_calls: list[object] = []
    recovery_calls: list[Path] = []
    confirmations: list[Path] = []
    strict_decrypt = page.service.decrypt_file
    legacy_recover = page.service.recover_legacy_file

    def record_strict_call(*args: object, **kwargs: object) -> object:
        strict_calls.append(kwargs.get("allow_legacy"))
        return strict_decrypt(*args, **kwargs)  # type: ignore[arg-type]

    def record_recovery(input_path: Path, *args: object, **kwargs: object) -> object:
        recovery_calls.append(input_path)
        return legacy_recover(input_path, *args, **kwargs)  # type: ignore[arg-type]

    def decline(_parent: object, _translator: object, input_path: Path) -> bool:
        confirmations.append(input_path)
        return False

    monkeypatch.setattr(page.service, "decrypt_file", record_strict_call)
    monkeypatch.setattr(page.service, "recover_legacy_file", record_recovery)
    monkeypatch.setattr(file_page_module, "confirm_legacy_file_recovery", decline)

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: bool(confirmations) and not page.controller.busy)

    assert strict_calls == [False]
    assert confirmations == [source]
    assert recovery_calls == []
    assert page.result.output_path is None
    assert page.alert.label.text() == "Legacy recovery was not started. No output was written."
    assert not (tmp_path / "legacy").exists()
    assert not list(tmp_path.glob(".*.tmp"))
    window.close()
    app.processEvents()


def test_file_legacy_recovery_runs_only_after_explicit_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app, window = _make_window(tmp_path)
    page = window.file_page
    source = tmp_path / "legacy.aes"
    plaintext = "逐字节恢复内容".encode()
    source.write_bytes(encrypt_legacy_bytes_for_tests(plaintext, "legacy-pass"))
    page.mode.set_current("decrypt")
    assert page.set_file(source)
    page.password.edit.setText("legacy-pass")

    strict_calls: list[object] = []
    recovery_calls: list[Path] = []
    confirmations: list[Path] = []
    strict_decrypt = page.service.decrypt_file
    legacy_recover = page.service.recover_legacy_file

    def record_strict_call(*args: object, **kwargs: object) -> object:
        strict_calls.append(kwargs.get("allow_legacy"))
        return strict_decrypt(*args, **kwargs)  # type: ignore[arg-type]

    def record_recovery(input_path: Path, *args: object, **kwargs: object) -> object:
        recovery_calls.append(input_path)
        return legacy_recover(input_path, *args, **kwargs)  # type: ignore[arg-type]

    def accept(_parent: object, _translator: object, input_path: Path) -> bool:
        confirmations.append(input_path)
        return True

    monkeypatch.setattr(page.service, "decrypt_file", record_strict_call)
    monkeypatch.setattr(page.service, "recover_legacy_file", record_recovery)
    monkeypatch.setattr(file_page_module, "confirm_legacy_file_recovery", accept)

    QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
    _wait_until(app, lambda: page.result.output_path is not None and not page.controller.busy)

    assert strict_calls == [False]
    assert confirmations == [source]
    assert recovery_calls == [source]
    assert page.result.output_path is not None
    assert page.result.output_path.read_bytes() == plaintext
    assert "weaker key derivation" in page.result.label.text()
    window.close()
    app.processEvents()


@pytest.mark.parametrize(
    ("language", "expected_title", "expected_action", "expected_warning"),
    [
        ("en-US", "Confirm legacy file recovery", "Recover legacy file", "plaintext output"),
        ("zh-CN", "确认恢复旧版文件", "恢复旧版文件", "明文输出"),
    ],
)
def test_legacy_recovery_confirmation_is_localized_and_cancel_is_default(
    language: str, expected_title: str, expected_action: str, expected_warning: str
) -> None:
    app = QApplication.instance() or QApplication([])
    dialog = LegacyRecoveryDialog(None, Translator(language), Path("C:/trusted/legacy.aes"))
    assert dialog.windowTitle() == expected_title
    assert dialog.recover_button.text() == expected_action
    assert expected_warning in dialog.warning_label.text()
    assert dialog.cancel_button.isDefault()
    assert dialog.recover_button.accessibleName() == expected_action
    dialog.show()
    QTest.mouseClick(dialog.cancel_button, Qt.MouseButton.LeftButton)
    assert dialog.result() == dialog.DialogCode.Rejected

    accepted_dialog = LegacyRecoveryDialog(None, Translator(language), Path("C:/trusted/legacy.aes"))
    accepted_dialog.show()
    QTest.mouseClick(accepted_dialog.recover_button, Qt.MouseButton.LeftButton)
    assert accepted_dialog.result() == accepted_dialog.DialogCode.Accepted
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
    assert window.shell.stack.currentIndex() == 1

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


def test_status_timeout_restarts_and_restores_localized_ready(tmp_path: Path) -> None:
    app, window = _make_window(tmp_path)
    status = window.shell.status
    status.show_message("first", 25)
    QTest.qWait(10)
    status.show_message("second", 90)
    QTest.qWait(35)
    app.processEvents()
    assert status.label.text() == "second"
    QTest.qWait(80)
    app.processEvents()
    assert status.label.text() == "Ready"
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
    assert dialog.ak_warning.text()
    assert dialog.overwrite_warning.text()

    QTest.mouseClick(dialog.clear_recent_button, Qt.MouseButton.LeftButton)
    dialog.reject()
    assert settings.recent_files == ["C:/private/a.txt"]

    dialog = SettingsDialog(translator, settings, store)
    dialog.advanced_toggle.setChecked(True)
    dialog.ak.setChecked(True)
    dialog.overwrite.setChecked(True)
    dialog.language_combo.setCurrentIndex(0)
    QTest.mouseClick(dialog.clear_recent_button, Qt.MouseButton.LeftButton)
    dialog.save()
    app.processEvents()
    assert settings.language == "zh-CN"
    assert settings.allow_ak_compatibility is True
    assert settings.overwrite_outputs is True
    assert settings.recent_files == []
    assert store.load().allow_ak_compatibility is True


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
    dialog.theme_combo.setCurrentIndex(1)
    errors: list[object] = []
    dialog.error.connect(lambda exc, _diagnostic: errors.append(exc))

    def fail_save(_candidate: AppSettings) -> None:
        raise ValidationError("injected settings limit", code="settings.too_large")

    monkeypatch.setattr(store, "save", fail_save)
    dialog.save()
    app.processEvents()

    assert settings.theme == "dark"
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
