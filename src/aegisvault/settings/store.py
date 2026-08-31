"""JSON settings persistence."""

from __future__ import annotations

import json
from pathlib import Path

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.file_io import atomic_binary_writer
from aegisvault.settings.models import AppSettings
from aegisvault.utils.paths import config_dir

SETTINGS_MAX_BYTES = 1024 * 1024


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config_dir() / "settings.json")

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            with self.path.open("rb") as source:
                raw = source.read(SETTINGS_MAX_BYTES + 1)
            if len(raw) > SETTINGS_MAX_BYTES:
                return AppSettings()
            data = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
            return AppSettings()
        if not isinstance(data, dict):
            return AppSettings()
        return AppSettings.from_dict(data)

    def save(self, settings: AppSettings) -> None:
        payload = (json.dumps(settings.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(payload) > SETTINGS_MAX_BYTES:
            raise ValidationError("Settings data exceeds the safety limit.", code="settings.too_large")
        with atomic_binary_writer(self.path, overwrite=True) as target:
            target.write(payload)
