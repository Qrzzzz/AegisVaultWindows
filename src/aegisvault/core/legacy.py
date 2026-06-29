"""Compatibility layer for AES Encryption System v2.0 data.

Legacy formats are supported for decryption and migration only:

* text: Base64(nonce + ciphertext)
* file: raw nonce + ciphertext
* AK#key#ciphertext: self-contained demonstration wrapper

The legacy key derivation is intentionally isolated here because it uses
``sha256(password)`` directly, which is not suitable for new encryption.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aegisvault.core.exceptions import AuthenticationError, CompatibilityError, ProtocolError, ValidationError
from aegisvault.core.models import TextDecryptResult

LEGACY_NONCE_SIZE = 12
LEGACY_MIN_SIZE = LEGACY_NONCE_SIZE + 16
LEGACY_FILE_MAX_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True)
class AkToken:
    key: str
    ciphertext: str


def is_ak_token(value: str) -> bool:
    return value.startswith("AK#")


def parse_ak_token(value: str) -> AkToken:
    parts = value.split("#", 2)
    if len(parts) != 3 or parts[0] != "AK" or not parts[1] or not parts[2]:
        raise CompatibilityError("Invalid AK compatibility token.", code="legacy.invalid_ak")
    return AkToken(key=parts[1], ciphertext=parts[2])


def legacy_key(password: str) -> bytes:
    if not password:
        raise ValidationError("Password is required for legacy decryption.", code="validation.password_required")
    return hashlib.sha256(password.encode("utf-8")).digest()


def decrypt_legacy_text(value: str, password: str | None = None) -> TextDecryptResult:
    bundled_key: str | None = None
    ciphertext = value.strip()
    if is_ak_token(ciphertext):
        token = parse_ak_token(ciphertext)
        bundled_key = token.key
        password = token.key
        ciphertext = token.ciphertext

    if not password:
        raise ValidationError("Password is required for legacy decryption.", code="validation.password_required")
    try:
        raw = base64.b64decode(ciphertext.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise ProtocolError("Legacy text is not valid Base64.", code="legacy.invalid_base64") from exc
    plaintext = decrypt_legacy_bytes(raw, password)
    try:
        text = plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("Legacy plaintext is not UTF-8 text.", code="legacy.invalid_text") from exc
    warning = "legacy_ak_risk" if bundled_key else "legacy_weak_kdf"
    return TextDecryptResult(text, "legacy-v2", warning, bundled_key)


def decrypt_legacy_bytes(data: bytes, password: str) -> bytes:
    if len(data) < LEGACY_MIN_SIZE:
        raise ProtocolError("Legacy data is too short.", code="legacy.truncated")
    nonce = data[:LEGACY_NONCE_SIZE]
    ciphertext = data[LEGACY_NONCE_SIZE:]
    aesgcm = AESGCM(legacy_key(password))
    try:
        return aesgcm.decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise AuthenticationError("Legacy authentication failed.", code="crypto.authentication_failed") from exc


def encrypt_legacy_text_for_tests(plaintext: str, password: str, nonce: bytes | None = None) -> str:
    """Create legacy text ciphertext for tests and migration fixtures."""

    nonce = nonce or b"\x00" * LEGACY_NONCE_SIZE
    aesgcm = AESGCM(legacy_key(password))
    return base64.b64encode(nonce + aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)).decode("ascii")


def encrypt_legacy_bytes_for_tests(data: bytes, password: str, nonce: bytes | None = None) -> bytes:
    """Create legacy file bytes for tests and migration fixtures."""

    nonce = nonce or b"\x01" * LEGACY_NONCE_SIZE
    aesgcm = AESGCM(legacy_key(password))
    return nonce + aesgcm.encrypt(nonce, data, None)
