from __future__ import annotations

import struct
from pathlib import Path

import pytest

from aegisvault.core.crypto import decrypt_file, encrypt_file
from aegisvault.core.exceptions import AuthenticationError, ProtocolError
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.protocol import (
    CHUNK_RECORD,
    FILE_MAGIC,
    MAX_CHUNK_SIZE,
    MIN_CHUNK_SIZE,
    canonical_json,
    read_file_header,
)


def fast_params() -> ScryptParams:
    return ScryptParams(salt=b"f" * 16, n=2**14)


def encrypt_fixture(tmp_path: Path, data: bytes, *, chunk_size: int = MIN_CHUNK_SIZE) -> tuple[Path, Path, Path]:
    source = tmp_path / "sample.bin"
    encrypted = tmp_path / "sample.bin.agv"
    restored = tmp_path / "sample.restored.bin"
    source.write_bytes(data)
    encrypt_file(source, encrypted, "passphrase", kdf_params=fast_params(), chunk_size=chunk_size)
    return source, encrypted, restored


def test_file_encrypt_decrypt_round_trip(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, bytes(range(256)) * 17)
    decrypt_file(encrypted, restored, "passphrase")
    assert restored.read_bytes() == bytes(range(256)) * 17


def test_multi_chunk_file_round_trip(tmp_path: Path) -> None:
    data = b"a" * (MIN_CHUNK_SIZE * 2 + 123)
    _source, encrypted, restored = encrypt_fixture(tmp_path, data)
    decrypt_file(encrypted, restored, "passphrase")
    assert restored.read_bytes() == data


@pytest.mark.parametrize(
    "size",
    [MIN_CHUNK_SIZE - 1, MIN_CHUNK_SIZE, MIN_CHUNK_SIZE + 1, MIN_CHUNK_SIZE * 2, MIN_CHUNK_SIZE * 2 + 1],
)
def test_file_round_trip_at_chunk_boundaries(tmp_path: Path, size: int) -> None:
    data = (bytes(range(256)) * ((size // 256) + 1))[:size]
    _source, encrypted, restored = encrypt_fixture(tmp_path, data)
    decrypt_file(encrypted, restored, "passphrase")
    assert restored.read_bytes() == data


def test_file_round_trip_with_unicode_directories_and_name(tmp_path: Path) -> None:
    directory = tmp_path / "目录 with spaces 🔐"
    directory.mkdir()
    source = directory / "源文件.数据"
    encrypted = directory / "加密输出.agv"
    restored = directory / "恢复文件.数据"
    source.write_bytes("路径与 Unicode 🔐".encode())

    encrypt_file(source, encrypted, "passphrase", kdf_params=fast_params(), chunk_size=MIN_CHUNK_SIZE)
    decrypt_file(encrypted, restored, "passphrase")

    assert restored.read_bytes() == source.read_bytes()


def test_empty_file_round_trip(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"")
    decrypt_file(encrypted, restored, "passphrase")
    assert restored.read_bytes() == b""


def test_file_wrong_password_fails(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"secret file")
    with pytest.raises(AuthenticationError):
        decrypt_file(encrypted, restored, "wrong")
    assert not restored.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_tampered_file_header_fails(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"secret file")
    blob = bytearray(encrypted.read_bytes())
    blob[len(FILE_MAGIC) + 4] ^= 0x01
    encrypted.write_bytes(bytes(blob))
    with pytest.raises(ProtocolError):
        decrypt_file(encrypted, restored, "passphrase")


def test_tampered_file_chunk_fails(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"secret file")
    blob = bytearray(encrypted.read_bytes())
    with encrypted.open("rb") as handle:
        _header, header_bytes = read_file_header(handle)
        chunk_start = len(FILE_MAGIC) + 4 + len(header_bytes) + CHUNK_RECORD.size
    blob[chunk_start] ^= 0x01
    encrypted.write_bytes(bytes(blob))
    with pytest.raises(AuthenticationError):
        decrypt_file(encrypted, restored, "passphrase")
    assert not restored.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_missing_final_chunk_fails(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"")
    with encrypted.open("rb") as handle:
        _header, header_bytes = read_file_header(handle)
    encrypted.write_bytes(encrypted.read_bytes()[: len(FILE_MAGIC) + 4 + len(header_bytes)])
    with pytest.raises(ProtocolError):
        decrypt_file(encrypted, restored, "passphrase")


def test_trailing_data_fails(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"secret file")
    encrypted.write_bytes(encrypted.read_bytes() + b"x")
    with pytest.raises(ProtocolError):
        decrypt_file(encrypted, restored, "passphrase")


def test_malicious_chunk_size_is_rejected(tmp_path: Path) -> None:
    _source, encrypted, restored = encrypt_fixture(tmp_path, b"secret file")
    with encrypted.open("rb") as handle:
        header, header_bytes = read_file_header(handle)
        rest = handle.read()
    header["chunk_size"] = MAX_CHUNK_SIZE + 1
    new_header = canonical_json(header)
    encrypted.write_bytes(FILE_MAGIC + struct.pack(">I", len(new_header)) + new_header + rest)
    with pytest.raises(ProtocolError):
        decrypt_file(encrypted, restored, "passphrase")


def test_header_size_limit_is_enforced(tmp_path: Path) -> None:
    source = tmp_path / "sample.bin"
    encrypted = tmp_path / "sample.bin.agv"
    source.write_bytes(b"x")
    with pytest.raises(ProtocolError):
        encrypt_file(source, encrypted, "passphrase", kdf_params=fast_params(), chunk_size=MAX_CHUNK_SIZE + 1)
