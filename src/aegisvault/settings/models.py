"""Persistent user settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AppSettings:
    language: str = "zh-CN"
    theme: str = "dark"
    default_output_dir: str = ""
    overwrite_outputs: bool = False
    remember_recent_files: bool = True
    show_advanced_options: bool = False
    allow_ak_compatibility: bool = False
    recent_files: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        settings = cls()
        for key in asdict(settings):
            if key in data:
                setattr(settings, key, data[key])
        if settings.language not in {"zh-CN", "en-US"}:
            settings.language = "zh-CN"
        if settings.theme not in {"dark", "light", "system"}:
            settings.theme = "dark"
        settings.recent_files = [str(item) for item in settings.recent_files if isinstance(item, str)][:20]
        return settings

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

