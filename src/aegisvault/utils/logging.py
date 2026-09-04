"""Logging setup that avoids sensitive content."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from aegisvault.utils.paths import log_dir

_SENSITIVE_LABELS = (
    r"password|passphrase|secret|token|api[_-]?key|encryption[_-]?key|bundled[_-]?key|ciphertext|plaintext"
)
_QUOTED_SECRET = re.compile(
    rf"(?i)(\b(?:{_SENSITIVE_LABELS})\b\s*[:=]\s*)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)"
)
_UNQUOTED_SECRET = re.compile(rf"(?i)(\b(?:{_SENSITIVE_LABELS})\b\s*[:=]\s*)[^\s,;\"']+")
_AGV1_TOKEN = re.compile(r"(?<![A-Za-z0-9_])AGV1\.[A-Za-z0-9_-]+={0,2}")
_AK_TOKEN = re.compile(r"(?<![A-Za-z0-9_])AK#[^#\s]+#[A-Za-z0-9+/=_-]+")
_QUOTED_PATH = re.compile(r"(?P<quote>[\"'])(?:[A-Za-z]:[\\/]|\\\\|/(?:home|Users|tmp|var|root)/).*?(?P=quote)")
_WINDOWS_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\)[^\r\n,;]+")
_POSIX_USER_PATH = re.compile(r"(?<![A-Za-z0-9])/(?:home|Users|tmp|var|root)/[^\r\n,;]+")


def redact_sensitive_text(value: object) -> str:
    """Return a log-safe representation of known secret and local-path forms."""

    text = str(value)
    text = _QUOTED_SECRET.sub(lambda match: f'{match.group(1)}{match.group("quote")}[REDACTED]{match.group("quote")}', text)
    text = _UNQUOTED_SECRET.sub(r"\1[REDACTED]", text)
    text = _AGV1_TOKEN.sub("AGV1.[REDACTED]", text)
    text = _AK_TOKEN.sub("AK#[REDACTED]", text)
    text = _QUOTED_PATH.sub(lambda match: f'{match.group("quote")}[PATH]{match.group("quote")}', text)
    text = _WINDOWS_PATH.sub("[PATH]", text)
    return _POSIX_USER_PATH.sub("[PATH]", text)


class RedactingFormatter(logging.Formatter):
    """Formatter that redacts both messages and rendered exception tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        if record.exc_text:
            record.exc_text = redact_sensitive_text(record.exc_text)
        return redact_sensitive_text(rendered)


def configure_logging(debug: bool = False) -> None:
    target_dir = log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if debug else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    formatter = RedactingFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = RotatingFileHandler(target_dir / "aegisvault.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.WARNING)
    root.addHandler(console)
