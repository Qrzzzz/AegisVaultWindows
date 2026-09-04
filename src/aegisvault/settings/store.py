"""JSON settings persistence."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path

from aegisvault.core.exceptions import ValidationError
from aegisvault.core.file_io import atomic_binary_writer
from aegisvault.core.models import CancelToken
from aegisvault.settings.locking import SETTINGS_LOCK_TIMEOUT, check_cancel, settings_lock
from aegisvault.settings.models import AppSettings
from aegisvault.utils.paths import config_dir

SETTINGS_MAX_BYTES = 1024 * 1024


class SettingsStore:
    def __init__(self, path: Path | None = None, *, lock_timeout: float = SETTINGS_LOCK_TIMEOUT) -> None:
        if not math.isfinite(lock_timeout) or lock_timeout < 0:
            raise ValueError("Settings lock timeout must be finite and nonnegative.")
        self.path = (path or (config_dir() / "settings.json")).expanduser().resolve()
        self.lock_timeout = lock_timeout

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            with self.path.open("rb") as source:
                raw = source.read(SETTINGS_MAX_BYTES + 1)
            if len(raw) > SETTINGS_MAX_BYTES:
                return AppSettings()
        except OSError:
            return AppSettings()
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError, RecursionError):
            # JSON's integer digit limit raises plain ValueError, not JSONDecodeError.
            # Keep model conversion outside this parsing-only recovery boundary.
            return AppSettings()
        if not isinstance(data, dict):
            return AppSettings()
        return AppSettings.from_dict(data)

    def save(self, settings: AppSettings) -> None:
        """Atomically replace a snapshot; read-modify-write callers must use update."""

        payload = (json.dumps(settings.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if len(payload) > SETTINGS_MAX_BYTES:
            raise ValidationError("Settings data exceeds the safety limit.", code="settings.too_large")
        with atomic_binary_writer(self.path, overwrite=True) as target:
            target.write(payload)

    def update(
        self, change: Callable[[AppSettings], AppSettings], *, cancel_token: CancelToken | None = None
    ) -> AppSettings:
        """Read the latest settings, apply a short change and save under one lock."""

        lock_path = self.path.with_name(f".{self.path.name}.lock")
        with settings_lock(lock_path, self.lock_timeout, cancel_token):
            settings = change(self.load())
            check_cancel(cancel_token)
            self.save(settings)
            return settings
