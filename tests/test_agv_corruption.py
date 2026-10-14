from __future__ import annotations

import struct
from pathlib import Path

import pytest

from aegisvault.core.crypto import decrypt_file, decrypt_text, encrypt_file
from aegisvault.core.exceptions import AppError, ProtocolError
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.protocol import (
    CHUNK_RECORD,
    FILE_MAGIC,
    HEADER_MAX_SIZE,
    TEXT_MAGIC,
    encode_token,
    parse_header,
    read_file_header,
)


def test_deep_header_maps_recursion_at_both_envelope_boundaries(tmp_path: Path) -> None:
    header = b'{"extra":' + b"[" * 30000 + b"0" + b"]" * 30000 + b"}"
    assert len(header) < HEADER_MAX_SIZE
    encrypted, restored = tmp_path / "deep.agv", tmp_path / "restored.bin"
    encrypted.write_bytes(FILE_MAGIC + struct.pack(">I", len(header)) + header)
    token = encode_token(TEXT_MAGIC + struct.pack(">I", len(header)) + header + b"x" * 16)
    for operation in (lambda: parse_header(header), lambda: decrypt_text(token, "audit-password"),
                      lambda: decrypt_file(encrypted, restored, "audit-password")):
        with pytest.raises(ProtocolError) as caught:
            operation()
        assert caught.value.code == "crypto.invalid_header"
    assert not restored.exists()
    assert not list(tmp_path.glob(".aegisvault-*.tmp"))


def _encrypted_fixture(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source.bin"
    encrypted = tmp_path / "source.bin.agv"
    source.write_bytes(b"authenticated data" * 100)
    encrypt_file(source, encrypted, "passphrase", kdf_params=ScryptParams(salt=b"z" * 16, n=2**14))
    return encrypted, tmp_path / "restored.bin"


@pytest.mark.parametrize("region", ["magic", "header", "chunk_record", "ciphertext"])
def test_random_corruption_fails(tmp_path: Path, region: str) -> None:
    encrypted, restored = _encrypted_fixture(tmp_path)
    blob = bytearray(encrypted.read_bytes())
    with encrypted.open("rb") as handle:
        _header, header_bytes = read_file_header(handle)
    header_start = len(FILE_MAGIC) + 4
    chunk_record_start = header_start + len(header_bytes)
    ciphertext_start = chunk_record_start + CHUNK_RECORD.size
    offsets = {
        "magic": 0,
        "header": header_start,
        "chunk_record": chunk_record_start,
        "ciphertext": ciphertext_start,
    }
    blob[offsets[region]] ^= 0x01
    encrypted.write_bytes(bytes(blob))
    with pytest.raises(AppError):
        decrypt_file(encrypted, restored, "passphrase")
