"""Shared dataclasses used across core and service layers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from threading import Event


@dataclass(frozen=True)
class ProgressEvent:
    """Progress update emitted by long-running operations."""

    percent: float
    stage: str
    detail: str = ""
    processed_bytes: int | None = None
    total_bytes: int | None = None


ProgressCallback = Callable[[ProgressEvent], None]


class TaskState(StrEnum):
    """Unified UI task states."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    DONE = "done"


class CancelToken:
    """Small thread-safe cancellation token."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class TextEncryptResult:
    ciphertext: str
    format_name: str


@dataclass(frozen=True)
class TextDecryptResult:
    plaintext: str
    format_name: str
    compatibility_warning: str | None = None
    bundled_key: str | None = None


@dataclass(frozen=True)
class FileProcessResult:
    input_path: Path
    output_path: Path
    original_size: int
    output_size: int
    format_name: str
    compatibility_warning: str | None = None
