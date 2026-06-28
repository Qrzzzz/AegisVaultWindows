"""Explicit Base64 utilities.

Base64 is encoding, not encryption. Keeping this in a separate module helps the
UI present it as a distinct workflow.
"""

from __future__ import annotations

import base64
import binascii

from aegisvault.core.exceptions import ValidationError


def encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def decode_text(encoded: str) -> str:
    try:
        return base64.b64decode(_clean_ascii(encoded), validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("Input is not valid UTF-8 Base64 text.", code="base64.invalid_text") from exc


def encode_bytes(data: bytes) -> bytes:
    return base64.b64encode(data)


def decode_bytes(encoded: bytes) -> bytes:
    try:
        return base64.b64decode(encoded.replace(b"\r", b"").replace(b"\n", b""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("Input is not valid Base64 data.", code="base64.invalid_data") from exc


def _clean_ascii(value: str) -> bytes:
    try:
        return value.strip().encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValidationError("Base64 input must be ASCII.", code="base64.invalid_text") from exc
