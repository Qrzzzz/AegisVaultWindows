"""Capture real Windows Qt workspaces using isolated, synthetic data."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--exercise", action="store_true", help="Run real synthetic round trips before result captures")
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "windows"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    from PySide6.QtCore import Qt, qVersion
    from PySide6.QtGui import QPalette
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QDialogButtonBox, QStyleFactory

    from aegisvault.i18n.translator import Translator
    from aegisvault.settings.models import AppSettings
    from aegisvault.settings.store import SettingsStore
    from aegisvault.ui.main_window import MainWindow
    from aegisvault.ui.pages.settings_page import SettingsDialog

    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aegisvault-windows-ui-") as temp:
        os.environ["APPDATA"] = os.environ["LOCALAPPDATA"] = temp
        app = QApplication([])
        before = app.style().objectName()
        settings = AppSettings(language="zh-CN")
        window = MainWindow(settings, SettingsStore(Path(temp) / "settings.json"), Translator(settings.language))
        window.show()
        app.processEvents()
        runtime = {
            "qt": qVersion(),
            "platform": app.platformName(),
            "style_before": before,
            "style_after": app.style().objectName(),
            "available_styles": QStyleFactory.keys(),
            "font": app.font().toString(),
            "stylesheet": app.styleSheet(),
            "window_color": app.palette().color(QPalette.ColorRole.Window).name(),
            "device_pixel_ratio": window.devicePixelRatioF(),
            "scale_factor": os.environ.get("QT_SCALE_FACTOR", "system"),
        }
        (args.output / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
        print(json.dumps(runtime), flush=True)
        for language in ("zh-CN", "en-US"):
            settings.language = language
            window._settings_saved()
            for width, height in ((900, 680), (600, 440)):
                window.resize(width, height)
                for index, name in enumerate(("text", "file", "base64")):
                    window._set_page(index)
                    app.processEvents()
                    QTest.qWait(150)
                    path = args.output / f"{name}-{language}-{width}x{height}.png"
                    assert window.grab().save(str(path))
        window.resize(900, 680)
        settings.language = "zh-CN"
        window._settings_saved()
        dialog = SettingsDialog(window.i18n, settings, window.store, window)
        dialog.show()
        QTest.qWait(100)
        assert dialog.grab().save(str(args.output / "settings-zh-CN.png"))
        dialog.close()
        if args.exercise:
            def run(page: object) -> None:
                assert page.run_button.isVisible() and page.run_button.isEnabled()
                QTest.mouseClick(page.run_button, Qt.MouseButton.LeftButton)
                deadline = time.monotonic() + 20
                while page.controller.busy and time.monotonic() < deadline:
                    QTest.qWait(10)
                assert not page.controller.busy, "Worker did not stop"
                app.processEvents()

            def capture(name: str) -> None:
                QTest.qWait(150)
                assert window.grab().save(str(args.output / f"{name}.png"))

            text = "本机加密测试 / Local encryption test\n中文、空格与换行均应保留。"
            page = window.text_page
            window._set_page(0)
            page.input.setPlainText(text)
            page.password.edit.setText("synthetic-qa-password")
            page.confirm_password.edit.setText("synthetic-qa-password")
            run(page)
            assert page.output.text().startswith("AGV1.")
            QTest.mouseClick(page.output.use_as_input_button, Qt.MouseButton.LeftButton)
            run(page)
            assert page.output.text() == text
            capture("text-result-zh-CN")
            page.password.edit.setText("wrong-qa-password")
            run(page)
            assert page.alert.isVisible() and page.output.text() == text
            capture("text-error-zh-CN")
            page.password.edit.setText("synthetic-qa-password")
            page.alert.clear()

            source = Path(temp) / "合成样例.txt"
            source.write_text(text, encoding="utf-8")
            page = window.file_page
            window._set_page(1)
            assert page.set_file(source)
            page.password.edit.setText("synthetic-qa-password")
            page.confirm_password.edit.setText("synthetic-qa-password")
            run(page)
            encrypted = page.result.output_path
            assert encrypted is not None and encrypted.is_file()
            capture("file-result-zh-CN")
            page.set_file(encrypted)
            page.mode.set_current("decrypt")
            run(page)
            assert page.result.output_path.read_bytes() == source.read_bytes()
            capture("file-decrypted-zh-CN")

            page = window.base64_page
            window._set_page(2)
            page.input.setPlainText(text)
            run(page)
            QTest.mouseClick(page.output.use_as_input_button, Qt.MouseButton.LeftButton)
            run(page)
            assert page.output.text() == text
            capture("base64-result-zh-CN")
            page.kind.set_current("file")
            page.mode.set_current("encode")
            page.set_file(source)
            run(page)
            encoded = page.result.output_path
            assert encoded is not None and encoded.is_file()
            capture("base64-file-result-zh-CN")
            page.set_file(encoded)
            page.mode.set_current("decode")
            run(page)
            assert page.result.output_path.read_bytes() == source.read_bytes()
            capture("base64-file-decoded-zh-CN")

            for language_index in (1, 0):
                dialog = SettingsDialog(window.i18n, settings, window.store, window)
                dialog.settings_saved.connect(window._settings_saved)
                dialog.language_combo.setCurrentIndex(language_index)
                dialog.show()
                QTest.mouseClick(dialog.buttons.button(QDialogButtonBox.StandardButton.Save), Qt.MouseButton.LeftButton)
                assert window.store.load().language == settings.language
                assert window.text_page.output.text() == text
                assert window.base64_page.output.text() == text
                for index, name in enumerate(("text", "file", "base64")):
                    window._set_page(index)
                    for size in ((900, 680), (600, 440)):
                        window.resize(*size)
                        capture(f"{name}-retained-{settings.language}-{size[0]}x{size[1]}")
            runtime["real_round_trips"] = ["AGV1 text", "AGV1 file", "Base64 text", "Base64 file"]
            runtime["settings_saved_and_results_retained"] = True
            (args.output / "runtime.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
            print("Real round trips, authentication error and settings persistence passed.", flush=True)
        window.resize(900, 680)
        window._set_page(0)
        if args.interactive:
            return app.exec()
        window.close()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
