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
        value = str(path.expanduser().resolve())

        def change(settings: AppSettings) -> AppSettings:
            if settings.remember_recent_files:
                files = [item for item in settings.recent_files if item != value]
                settings.recent_files = ([value] + files)[: self.max_items]
            return settings

        self.settings = self.store.update(change)

    def clear(self) -> None:
        def change(settings: AppSettings) -> AppSettings:
            settings.recent_files = []
            return settings

        self.settings = self.store.update(change)
