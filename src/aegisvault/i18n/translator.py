"""Small JSON based translation manager."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

SUPPORTED_LANGUAGES = ("zh-CN", "en-US")


class Translator:
    def __init__(self, language: str = "zh-CN") -> None:
        self._messages: dict[str, dict[str, str]] = {}
        for lang in SUPPORTED_LANGUAGES:
            self._messages[lang] = self._load(lang)
        self.language = language if language in SUPPORTED_LANGUAGES else "zh-CN"

    def set_language(self, language: str) -> None:
        if language in SUPPORTED_LANGUAGES:
            self.language = language

    def t(self, key: str, **kwargs: Any) -> str:
        value = self._messages.get(self.language, {}).get(key)
        if value is None:
            value = self._messages["en-US"].get(key, key)
        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        return value

    def _load(self, language: str) -> dict[str, str]:
        target = resources.files("aegisvault.i18n.locales").joinpath(f"{language}.json")
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return {str(key): str(value) for key, value in data.items()}

