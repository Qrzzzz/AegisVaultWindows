from __future__ import annotations

import json
from pathlib import Path

from aegisvault.i18n.translator import SUPPORTED_LANGUAGES, Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore


def test_settings_load_save(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(language="en-US", default_output_dir=str(tmp_path), allow_ak_compatibility=True)
    store.save(settings)
    loaded = store.load()
    assert loaded.language == "en-US"
    assert loaded.default_output_dir == str(tmp_path)
    assert loaded.allow_ak_compatibility is True


def test_i18n_keys_are_complete() -> None:
    base: set[str] | None = None
    for language in SUPPORTED_LANGUAGES:
        with Path("src/aegisvault/i18n/locales", f"{language}.json").open("r", encoding="utf-8") as handle:
            keys = set(json.load(handle))
        if base is None:
            base = keys
        else:
            assert keys == base
    translator = Translator("en-US")
    assert translator.t("app.title") == "AegisVault"
