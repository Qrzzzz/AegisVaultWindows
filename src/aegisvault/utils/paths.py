"""Runtime path helpers for development and bundled builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from aegisvault import __app_name__


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    """Return a resource path that also works under PyInstaller."""

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).joinpath("aegisvault", "resources", *parts)
    return package_root().joinpath("resources", *parts)


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / __app_name__
    return Path.home() / ".config" / __app_name__.lower()


def log_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / __app_name__ / "Logs"
    return Path.home() / ".local" / "state" / __app_name__.lower() / "logs"
