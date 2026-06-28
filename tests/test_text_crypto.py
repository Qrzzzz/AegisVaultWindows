from __future__ import annotations

import pytest

from aegisvault.core.crypto import decrypt_text, decrypt_text_auto, encrypt_text
from aegisvault.core.exceptions import AuthenticationError, CompatibilityError, ProtocolError
from aegisvault.core.kdf import SCRYPT_N_MAX, ScryptParams
from aegisvault.core.legacy import encrypt_legacy_text_for_tests
from aegisvault.core.protocol import (
    HEADER_MAX_SIZE,
    TEXT_MAGIC,
    decode_token,
    encode_token,
    pack_envelope,
    unpack_envelope,
)
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings


def fast_params() -> ScryptParams:
    return ScryptParams(salt=b"t" * 16, n=2**14)


def test_text_encrypt_decrypt_round_trip() -> None:
    token = encrypt_text("secret text", "passphrase", kdf_params=fast_params()).ciphertext
    assert token.startswith("AGV1.")
    assert decrypt_text(token, "passphrase").plaintext == "secret text"


def test_wrong_password_fails_authentication() -> None:
    token = encrypt_text("secret", "right", kdf_params=fast_params()).ciphertext
    with pytest.raises(AuthenticationError):
        decrypt_text(token, "wrong")


def test_tampered_text_fails_authentication_or_protocol() -> None:
    token = encrypt_text("secret", "right", kdf_params=fast_params()).ciphertext
    package = bytearray(decode_token(token))
    package[-1] ^= 0x01
    with pytest.raises((AuthenticationError, ProtocolError)):
        decrypt_text(encode_token(bytes(package)), "right")


def test_malicious_text_kdf_is_rejected_before_derivation() -> None:
    token = encrypt_text("secret", "right", kdf_params=fast_params()).ciphertext
    header, _header_bytes, ciphertext = unpack_envelope(TEXT_MAGIC, decode_token(token))
    header["kdf"]["n"] = SCRYPT_N_MAX * 2
    malicious = encode_token(pack_envelope(TEXT_MAGIC, header, ciphertext))
    with pytest.raises(ProtocolError):
        decrypt_text(malicious, "right")


def test_header_size_limit_is_enforced() -> None:
    with pytest.raises(ProtocolError):
        pack_envelope(TEXT_MAGIC, {"format": "aegisvault.text", "padding": "x" * HEADER_MAX_SIZE}, b"")


def test_legacy_text_compatibility() -> None:
    legacy = encrypt_legacy_text_for_tests("old text", "legacy-pass")
    result = decrypt_text_auto(legacy, "legacy-pass")
    assert result.plaintext == "old text"
    assert result.format_name == "legacy-v2"
    assert result.compatibility_warning == "legacy_weak_kdf"


def test_ak_compatibility_default_closed() -> None:
    legacy = encrypt_legacy_text_for_tests("portable", "bundled-key")
    service = CryptoService(AppSettings())
    with pytest.raises(CompatibilityError):
        service.decrypt_text(f"AK#bundled-key#{legacy}", None)


def test_ak_compatibility_enabled_warns() -> None:
    legacy = encrypt_legacy_text_for_tests("portable", "bundled-key")
    service = CryptoService(AppSettings(allow_ak_compatibility=True))
    result = service.decrypt_text(f"AK#bundled-key#{legacy}", None)
    assert result.plaintext == "portable"
    assert result.bundled_key == "bundled-key"
    assert result.compatibility_warning == "legacy_ak_risk"
