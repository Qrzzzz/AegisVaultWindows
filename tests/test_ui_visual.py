# ruff: noqa: E402, I001
"""Offscreen UI fixtures: isolated config, native controls, no network or real secrets."""

from __future__ import annotations

import os
import argparse
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtGui import QFontDatabase, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from aegisvault.core.exceptions import ProtocolError
from aegisvault.core.models import FileProcessResult, TextDecryptResult
from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.ui.main_window import MainWindow
from aegisvault.ui.pages.settings_page import SettingsDialog

BASELINE_DIR = ROOT / "docs" / "screenshots"
PAGE_NAMES = ("text", "file", "base64")


def qa_application() -> QApplication:
    app = QApplication.instance() or QApplication([])
    # Offscreen Windows cannot discover installed font files by itself. These
    # registrations belong only to QA, not to the application's font policy.
    if not app.property("qaFontsLoaded"):
        for name in ("segoeui.ttf", "msyh.ttc"):
            path = Path("C:/Windows/Fonts") / name
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))
        app.setProperty("qaFontsLoaded", True)
    return app


def render_workspace(
    path: Path,
    page_index: int = 0,
    *,
    language: str = "zh-CN",
    window_size: tuple[int, int] = (900, 680),
    scenario: str = "idle",
) -> QImage:
    with tempfile.TemporaryDirectory(prefix="aegisvault-ui-") as temp_dir:
        temp = Path(temp_dir)
        with patch.dict(os.environ, {"APPDATA": str(temp), "LOCALAPPDATA": str(temp)}):
            app = qa_application()
            settings = AppSettings(language=language, theme="dark")
            store = SettingsStore(temp / "settings.json")
            window = MainWindow(settings, store, Translator(language))
            window.resize(*window_size)
            target: QWidget = window
            if scenario == "text-result":
                window.text_page.mode.set_current("decrypt")
                window.text_page.input.setPlainText("AGV1. [visual fixture / 截图示例]")
                window.text_page._on_success(
                    TextDecryptResult("本机处理，不上传内容。\nProcessed locally; nothing is uploaded.", "AGV1")
                )
            elif scenario == "file-result":
                page_index = 1
                source = Path("C:/Samples/report.txt")
                page = window.file_page
                page.selected_file = source
                page._refresh_preview()
                page.picker.set_file(
                    source, {window.i18n.t("file.size_label"): "128 B", window.i18n.t("file.type_label"): ".txt"}
                )
                page._on_success(FileProcessResult(source, Path("C:/Samples/report.txt.agv"), 128, 242, "AGV1"))
            elif scenario == "error":
                window.text_page.password.edit.setText("fixture-only")
                window.text_page.run_current()
            elif scenario == "file-decrypt":
                page_index = 1
                window.file_page.mode.set_current("decrypt")
            elif scenario == "unsupported":
                window.text_page.mode.set_current("decrypt")
                window.text_page._on_failed(
                    ProtocolError("Static screenshot fixture", code="protocol.unsupported_format"), ""
                )
            elif scenario in {"settings", "advanced"}:
                target = SettingsDialog(window.i18n, settings, store, window)
                if scenario == "advanced":
                    target.advanced_toggle.setChecked(True)
            window._set_page(page_index, focus=False)
            window.show()
            if target is not window:
                target.show()
            app.processEvents()
            QTest.qWait(80)
            image = target.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
            path.parent.mkdir(parents=True, exist_ok=True)
            assert image.save(str(path), "PNG")
            target.close()
            window.close()
            app.processEvents()
            return image


def _sample_difference(left: QImage, right: QImage) -> float:
    assert left.size() == right.size()
    difference = 0
    samples = 0
    for y in range(0, left.height(), 8):
        for x in range(0, left.width(), 8):
            a, b = left.pixelColor(x, y), right.pixelColor(x, y)
            difference += abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())
            samples += 1
    return difference / max(1, samples * 255 * 3)


def test_offscreen_workspace_screenshots_match_light_baselines(tmp_path: Path) -> None:
    for index, name in enumerate(PAGE_NAMES):
        rendered = render_workspace(tmp_path / f"{name}.png", index)
        baseline_path = BASELINE_DIR / f"minimal-{name}-zh-CN.png"
        baseline = QImage(str(baseline_path)).convertToFormat(QImage.Format.Format_RGB32)
        assert not baseline.isNull(), f"Missing UI baseline: {baseline_path}"
        assert rendered.size() == baseline.size()
        assert rendered.width() == 900 and rendered.height() == 680
        assert _sample_difference(rendered, baseline) < 0.06
        assert rendered.pixelColor(2, 50).lightness() > 180


def _update_baselines(qa_dir: Path | None = None) -> None:
    if os.environ["QT_SCALE_FACTOR"] != "1":
        if qa_dir is None:
            raise SystemExit("High-DPI samples require --qa-dir (they are not committed baselines).")
        for index, name in enumerate(PAGE_NAMES):
            target = qa_dir / f"basic-{name}-150pct.png"
            render_workspace(target, index, window_size=(640, 480))
            print(target)
        return
    for language in ("zh-CN", "en-US"):
        destination = BASELINE_DIR if language == "zh-CN" else qa_dir
        if destination is None:
            continue
        for index, name in enumerate(PAGE_NAMES):
            target = destination / f"minimal-{name}-{language}.png"
            render_workspace(target, index, language=language)
            print(target)
    for scenario in ("text-result", "file-result", "file-decrypt", "error", "unsupported", "settings", "advanced"):
        destination = BASELINE_DIR if scenario in {"text-result", "settings"} else qa_dir
        if destination is None:
            continue
        target = destination / f"basic-{scenario}.png"
        render_workspace(target, scenario=scenario)
        print(target)
    if qa_dir is not None:
        for index, name in enumerate(PAGE_NAMES):
            target = qa_dir / f"basic-{name}-small.png"
            render_workspace(target, index, window_size=(640, 480))
            print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--qa-dir", type=Path)
    args = parser.parse_args()
    if not args.update:
        raise SystemExit("Pass --update to regenerate the isolated UI fixtures.")
    _update_baselines(args.qa_dir)
