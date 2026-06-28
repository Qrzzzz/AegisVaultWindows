from __future__ import annotations

from pathlib import Path

import pytest

from aegisvault.core.crypto import decrypt_file, encrypt_file
from aegisvault.core.exceptions import AppError
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.protocol import CHUNK_RECORD, FILE_MAGIC, read_file_header


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
