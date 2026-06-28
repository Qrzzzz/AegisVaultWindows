"""Privacy-aware recent file tracking."""

from __future__ import annotations

from pathlib import Path

from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore


class RecentFilesService:
    def __init__(self, settings: AppSettings, store: SettingsStore, *, max_items: int = 12) -> None:
        self.settings = settings
        self.store = store
        self.max_items = max_items

    def add(self, path: Path) -> None:
        if not self.settings.remember_recent_files:
            return
        value = str(path.expanduser().resolve())
        files = [item for item in self.settings.recent_files if item != value]
        files.insert(0, value)
        self.settings.recent_files = files[: self.max_items]
        self.store.save(self.settings)

    def clear(self) -> None:
        self.settings.recent_files = []
        self.store.save(self.settings)

