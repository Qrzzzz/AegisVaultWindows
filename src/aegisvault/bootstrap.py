"""Application bootstrap."""

from __future__ import annotations

import os

from aegisvault.i18n.translator import Translator
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.utils.logging import configure_logging


def bootstrap() -> tuple[SettingsStore, AppSettings, Translator]:
    debug = os.environ.get("AEGISVAULT_DEBUG") == "1"
    configure_logging(debug=debug)
    store = SettingsStore()
    settings = store.load()
    translator = Translator(settings.language)
    return store, settings, translator
