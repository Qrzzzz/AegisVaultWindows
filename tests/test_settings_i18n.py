from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import aegisvault.core.file_io as core_file_io
from aegisvault.core.exceptions import FileIOError, ValidationError
from aegisvault.i18n.translator import SUPPORTED_LANGUAGES, Translator
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SETTINGS_MAX_BYTES, SettingsStore


def test_settings_load_save(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    settings = AppSettings(language="en-US", default_output_dir=str(tmp_path), show_advanced_options=True)
    store.save(settings)
    loaded = store.load()
    assert loaded.language == "en-US"
    assert loaded.default_output_dir == str(tmp_path)
    assert loaded.show_advanced_options is True


def test_settings_load_rejects_wrong_field_types(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "language": 1,
                "theme": ["dark"],
                "default_output_dir": [str(tmp_path)],
                "overwrite_outputs": "false",
                "remember_recent_files": 1,
                "show_advanced_options": None,
                "recent_files": "C:/secret.txt",
            }
        ),
        encoding="utf-8",
    )

    loaded = SettingsStore(path).load()

    assert loaded == AppSettings()


@pytest.mark.parametrize("removed_flag", [True, False, "true", 1, None])
def test_removed_settings_flag_is_ignored_without_resetting_other_preferences(
    tmp_path: Path, removed_flag: object
) -> None:
    path = tmp_path / "settings.json"
    expected = AppSettings(
        language="en-US",
        default_output_dir=str(tmp_path),
        overwrite_outputs=True,
        remember_recent_files=False,
        show_advanced_options=True,
        recent_files=["文档 🔐.agv"],
    )
    data = expected.to_dict() | {"allow_ak_compatibility": removed_flag}
    original = json.dumps(data, ensure_ascii=False).encode("utf-8")
    path.write_bytes(original)
    store = SettingsStore(path)

    loaded = store.load()

    assert loaded == expected
    assert not hasattr(loaded, "allow_ak_compatibility")
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]

    store.save(loaded)

    assert json.loads(path.read_text(encoding="utf-8")) == expected.to_dict()
    assert store.load() == expected
    assert list(tmp_path.iterdir()) == [path]


def test_settings_save_rejects_invalid_runtime_types(tmp_path: Path) -> None:
    settings = AppSettings()
    settings.overwrite_outputs = "false"  # type: ignore[assignment]

    with pytest.raises(ValidationError):
        SettingsStore(tmp_path / "settings.json").save(settings)


def test_settings_save_is_atomic_and_preserves_previous_file_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "settings.json"
    previous = b'{"language":"zh-CN"}'
    path.write_bytes(previous)

    def fail_replace(_source: object, _target: object) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(core_file_io.os, "replace", fail_replace)

    with pytest.raises(FileIOError):
        SettingsStore(path).save(AppSettings(language="en-US"))

    assert path.read_bytes() == previous
    assert not list(tmp_path.glob(".*.tmp"))


def test_crypto_service_rejects_invalid_in_memory_settings() -> None:
    settings = AppSettings()
    settings.overwrite_outputs = "true"  # type: ignore[assignment]

    with pytest.raises(ValidationError):
        CryptoService(settings)


def test_settings_load_discards_nul_containing_paths(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"default_output_dir": "bad\u0000path", "recent_files": ["ok.txt", "bad\u0000path"]}),
        encoding="utf-8",
    )

    loaded = SettingsStore(path).load()

    assert loaded.default_output_dir == ""
    assert loaded.recent_files == ["ok.txt"]
    loaded.validate()


@pytest.mark.parametrize("raw", [b"\xff\xfe", b"[not json"])
def test_settings_load_falls_back_for_malformed_bytes(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(raw)
    assert SettingsStore(path).load() == AppSettings()


def test_settings_size_limit_applies_to_load_and_save(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(b" " * (SETTINGS_MAX_BYTES + 1))
    assert SettingsStore(path).load() == AppSettings()

    settings = AppSettings(default_output_dir="x" * SETTINGS_MAX_BYTES)
    with pytest.raises(ValidationError) as caught:
        SettingsStore(path).save(settings)
    assert caught.value.code == "settings.too_large"
    assert path.stat().st_size == SETTINGS_MAX_BYTES + 1
    assert not list(tmp_path.glob(".*.tmp"))


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


def test_ui_literal_translation_keys_exist_in_every_locale() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/aegisvault/ui").rglob("*.py"))
    literal_keys = set(re.findall(r'\.t\("([^"]+)"', source))
    for language in SUPPORTED_LANGUAGES:
        path = Path("src/aegisvault/i18n/locales", f"{language}.json")
        messages = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(literal_keys - set(messages))
        assert not missing, f"{language} is missing UI keys: {missing}"
        assert all(str(messages[key]).strip() for key in literal_keys)


def test_integrated_backend_error_codes_have_specific_bilingual_messages() -> None:
    integrated_codes = (
        "crypto.size_mismatch",
        "file.input_changed",
        "file.read_failed",
        "file.same_input_output",
        "protocol.unsupported_format",
        "resource.limit_exceeded",
        "settings.invalid_type",
        "settings.invalid_value",
        "settings.too_large",
    )
    for language in SUPPORTED_LANGUAGES:
        translator = Translator(language)
        generic = translator.t("error.generic")
        for code in integrated_codes:
            key = f"error.{code}"
            message = translator.t(key)
            assert message not in {key, generic}, f"{language} has no specific message for {code}"
