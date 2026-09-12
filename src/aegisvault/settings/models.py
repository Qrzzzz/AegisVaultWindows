"""Persistent user settings."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TypeGuard

from aegisvault.core.exceptions import ValidationError

SUPPORTED_THEMES = {"dark", "light", "system"}
SUPPORTED_LANGUAGES = {"zh-CN", "en-US"}
MAX_RECENT_FILES = 20


def _valid_path_text(value: object) -> TypeGuard[str]:
    if type(value) is not str or "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


@dataclass
class AppSettings:
    language: str = "zh-CN"
    theme: str = "light"
    default_output_dir: str = ""
    overwrite_outputs: bool = False
    remember_recent_files: bool = True
    show_advanced_options: bool = False
    recent_files: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        defaults = cls()
        if not isinstance(data, dict):
            return defaults

        language = data.get("language")
        theme = data.get("theme")
        default_output_dir = data.get("default_output_dir")
        recent_files = data.get("recent_files")
        return cls(
            language=language if type(language) is str and language in SUPPORTED_LANGUAGES else defaults.language,
            theme=theme if type(theme) is str and theme in SUPPORTED_THEMES else defaults.theme,
            default_output_dir=(
                default_output_dir
                if _valid_path_text(default_output_dir)
                else defaults.default_output_dir
            ),
            overwrite_outputs=cls._bool_or_default(data.get("overwrite_outputs"), defaults.overwrite_outputs),
            remember_recent_files=cls._bool_or_default(
                data.get("remember_recent_files"), defaults.remember_recent_files
            ),
            show_advanced_options=cls._bool_or_default(
                data.get("show_advanced_options"), defaults.show_advanced_options
            ),
            recent_files=(
                [item for item in recent_files if _valid_path_text(item)][:MAX_RECENT_FILES]
                if type(recent_files) is list
                else []
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    def validate(self) -> None:
        """Validate runtime values before services persist or consume them."""

        if type(self.language) is not str or self.language not in SUPPORTED_LANGUAGES:
            raise ValidationError("Invalid settings language.", code="settings.invalid_value")
        if type(self.theme) is not str or self.theme not in SUPPORTED_THEMES:
            raise ValidationError("Invalid settings theme.", code="settings.invalid_value")
        if type(self.default_output_dir) is not str or "\x00" in self.default_output_dir:
            raise ValidationError("Invalid settings output directory.", code="settings.invalid_type")
        if not _valid_path_text(self.default_output_dir):
            raise ValidationError("Invalid Unicode in settings output directory.", code="settings.invalid_value")
        boolean_values = (
            self.overwrite_outputs,
            self.remember_recent_files,
            self.show_advanced_options,
        )
        if any(type(value) is not bool for value in boolean_values):
            raise ValidationError("Invalid Boolean settings value.", code="settings.invalid_type")
        if type(self.recent_files) is not list or len(self.recent_files) > MAX_RECENT_FILES:
            raise ValidationError("Invalid recent-files settings value.", code="settings.invalid_type")
        if any(type(item) is not str or "\x00" in item for item in self.recent_files):
            raise ValidationError("Invalid recent-files entry.", code="settings.invalid_type")
        if any(not _valid_path_text(item) for item in self.recent_files):
            raise ValidationError("Invalid Unicode in recent-files entry.", code="settings.invalid_value")

    @staticmethod
    def _bool_or_default(value: object, default: bool) -> bool:
        return value if type(value) is bool else default
