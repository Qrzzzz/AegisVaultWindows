"""Explicit Base64 utilities.

Base64 is encoding, not encryption. Keeping this in a separate module helps the
UI present it as a distinct workflow.
"""

from __future__ import annotations

import base64
import binascii
import re

from aegisvault.core.exceptions import ValidationError


def encode_text(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


ASCII_WHITESPACE = re.compile(rb"[\t\n\r\f\v ]+")


def decode_text(encoded: str, *, strict: bool = True, ignore_ascii_whitespace: bool = False) -> str:
    try:
        return decode_bytes(
            _ascii_bytes(encoded),
            strict=strict,
            ignore_ascii_whitespace=ignore_ascii_whitespace,
        ).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ValidationError("Input is not valid UTF-8 Base64 text.", code="base64.invalid_text") from exc


def encode_bytes(data: bytes) -> bytes:
    return base64.b64encode(data)


def decode_bytes(encoded: bytes, *, strict: bool = True, ignore_ascii_whitespace: bool = False) -> bytes:
    try:
        data = _prepare_base64(encoded, strict=strict, ignore_ascii_whitespace=ignore_ascii_whitespace)
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("Input is not valid Base64 data.", code="base64.invalid_data") from exc


def _ascii_bytes(value: str) -> bytes:
    try:
        return value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValidationError("Base64 input must be ASCII.", code="base64.invalid_text") from exc


def _prepare_base64(value: bytes, *, strict: bool, ignore_ascii_whitespace: bool) -> bytes:
    try:
        value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValidationError("Base64 input must be ASCII.", code="base64.invalid_data") from exc
    if strict and ASCII_WHITESPACE.search(value):
        raise ValidationError("Base64 input contains whitespace in strict mode.", code="base64.invalid_data")
    if ignore_ascii_whitespace:
        return ASCII_WHITESPACE.sub(b"", value)
    return value
