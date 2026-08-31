from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

import pytest

from aegisvault.core.crypto import decrypt_file, decrypt_text, encrypt_file, encrypt_text
from aegisvault.core.exceptions import ProtocolError
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.protocol import (
    MIN_CHUNK_SIZE,
    canonical_json,
    decode_token,
    parse_header,
    validate_chunk_size,
    validate_common_header,
    validate_file_header,
    validate_text_header,
)

FIXED_PASSWORD = "pässwörd-密钥"
FIXED_PLAINTEXT = "AegisVault 固定样本 🔐"
FIXED_TEXT_TOKEN = (
    "AGV1.QUdWVEVYVAEAAADdeyJhbGdvcml0aG0iOiJBRVMtMjU2LUdDTSIsImNyZWF0ZWRfYXQiOiIyMDI2LTAxLTAyVDAzOjA0OjA1WiIs"
    "ImZvcm1hdCI6ImFlZ2lzdmF1bHQudGV4dCIsImtkZiI6eyJsZW5ndGgiOjMyLCJuIjoxNjM4NCwicCI6MSwiciI6OCwic2FsdCI6IkFBRUNB"
    "d1FGQmdjSUNRb0xEQTBPRHc9PSIsInR5cGUiOiJzY3J5cHQifSwibm9uY2UiOiJBQUVDQXdRRkJnY0lDUW9MIiwidmVyc2lvbiI6MX2Rd050"
    "x4GMXm_fKdfMEEoReZ9_d7p2j-w_0owvc_G-cOe5SLUWGD6HgmBEPA"
)
FIXED_FILE_BASE64 = (
    "QUdWRklMRQEAAAE9eyJhbGdvcml0aG0iOiJBRVMtMjU2LUdDTSIsImNodW5rX3NpemUiOjY1NTM2LCJjcmVhdGVkX2F0IjoiMjAyNi0wMS0w"
    "MlQwMzowNDowNVoiLCJmb3JtYXQiOiJhZWdpc3ZhdWx0LmZpbGUiLCJrZGYiOnsibGVuZ3RoIjozMiwibiI6MTYzODQsInAiOjEsInIiOjgs"
    "InNhbHQiOiJBQUVDQXdRRkJnY0lDUW9MREEwT0R3PT0iLCJ0eXBlIjoic2NyeXB0In0sIm1ldGFkYXRhIjp7Im9yaWdpbmFsX3NpemUiOjMw"
    "LCJvcmlnaW5hbF9zdWZmaXgiOiIudHh0In0sIm1vZGUiOiJjaHVua2VkIiwibm9uY2VfcHJlZml4IjoiQUFFQ0F3UUZCZ2M9IiwidmVyc2lv"
    "biI6MX0BAAAALrjYvC0rePP2d1O0AWEcKbX9pQ0QQkx6teLZhWAGILGLCx/zq/qmLn6IXNdUD74="
)


def fixed_params() -> ScryptParams:
    return ScryptParams(salt=bytes(range(16)), n=2**14, r=8, p=1, length=32)


def test_fixed_agv1_text_fixture_decrypts() -> None:
    assert decrypt_text(FIXED_TEXT_TOKEN, FIXED_PASSWORD).plaintext == FIXED_PLAINTEXT


def test_agv1_text_writer_remains_byte_compatible_with_fixed_fixture() -> None:
    with (
        patch("aegisvault.core.crypto.os.urandom", return_value=bytes(range(12))),
        patch("aegisvault.core.crypto.now_utc", return_value="2026-01-02T03:04:05Z"),
    ):
        result = encrypt_text(FIXED_PLAINTEXT, FIXED_PASSWORD, kdf_params=fixed_params())
    assert result.ciphertext == FIXED_TEXT_TOKEN


def test_fixed_agv1_file_fixture_decrypts(tmp_path: Path) -> None:
    encrypted = tmp_path / "固定样本.agv"
    restored = tmp_path / "恢复 🔐.txt"
    encrypted.write_bytes(base64.b64decode(FIXED_FILE_BASE64, validate=True))

    decrypt_file(encrypted, restored, FIXED_PASSWORD)

    assert restored.read_bytes() == "AegisVault 固定文件样本\n".encode()


def test_agv1_file_writer_remains_byte_compatible_with_fixed_fixture(tmp_path: Path) -> None:
    source = tmp_path / "固定样本.txt"
    encrypted = tmp_path / "fixed.agv"
    source.write_bytes("AegisVault 固定文件样本\n".encode())
    with (
        patch("aegisvault.core.crypto.os.urandom", return_value=bytes(range(8))),
        patch("aegisvault.core.crypto.now_utc", return_value="2026-01-02T03:04:05Z"),
    ):
        encrypt_file(
            source,
            encrypted,
            FIXED_PASSWORD,
            kdf_params=fixed_params(),
            chunk_size=MIN_CHUNK_SIZE,
        )
    assert base64.b64encode(encrypted.read_bytes()).decode("ascii") == FIXED_FILE_BASE64


def test_text_token_rejects_non_urlsafe_base64_alphabet() -> None:
    with pytest.raises(ProtocolError) as caught:
        decode_token("AGV1.!!!!")
    assert caught.value.code == "crypto.invalid_encoding"


def test_protocol_version_rejects_boolean_alias_for_one() -> None:
    with pytest.raises(ProtocolError):
        validate_common_header(
            {"format": "aegisvault.text", "version": True, "algorithm": "AES-256-GCM"},
            kind="text",
        )


def test_chunk_size_rejects_coercible_string() -> None:
    with pytest.raises(ProtocolError):
        validate_chunk_size(str(MIN_CHUNK_SIZE))


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {"original_suffix": ".txt"},
        {"original_suffix": ".txt", "original_size": True},
        {"original_suffix": 1, "original_size": 0},
        {"original_suffix": "bad\x00suffix", "original_size": 0},
    ],
)
def test_file_header_rejects_malformed_metadata(metadata: object) -> None:
    header = {
        "format": "aegisvault.file",
        "version": 1,
        "algorithm": "AES-256-GCM",
        "mode": "chunked",
        "kdf": {},
        "chunk_size": MIN_CHUNK_SIZE,
        "nonce_prefix": "AAECAwQFBgc=",
        "metadata": metadata,
        "created_at": "2026-01-02T03:04:05Z",
    }
    with pytest.raises(ProtocolError):
        validate_file_header(header)


@pytest.mark.parametrize("field", ["created_at", "kdf", "nonce"])
def test_text_header_requires_all_typed_fields(field: str) -> None:
    header: dict[str, object] = {
        "format": "aegisvault.text",
        "version": 1,
        "algorithm": "AES-256-GCM",
        "kdf": {},
        "nonce": "AAECAwQFBgcICQoL",
        "created_at": "2026-01-02T03:04:05Z",
    }
    header[field] = None
    with pytest.raises(ProtocolError):
        validate_text_header(header)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"format":"a","format":"b"}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
    ],
)
def test_protocol_header_rejects_ambiguous_or_non_standard_json(raw: bytes) -> None:
    with pytest.raises(ProtocolError):
        parse_header(raw)


def test_protocol_writer_rejects_non_finite_json_values() -> None:
    with pytest.raises(ProtocolError):
        canonical_json({"value": float("nan")})
