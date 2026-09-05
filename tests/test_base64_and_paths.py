from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

import aegisvault.core.file_io as core_file_io
from aegisvault.core import base64_tools
from aegisvault.core.exceptions import FileIOError, ValidationError
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import (
    base64_encoded_output_path,
    decrypted_output_path,
    encrypted_output_path,
    unique_path,
)
from aegisvault.settings.models import AppSettings


def test_base64_text_round_trip() -> None:
    encoded = base64_tools.encode_text("hello")
    assert base64_tools.decode_text(encoded) == "hello"


def test_base64_invalid_text_raises() -> None:
    with pytest.raises(ValidationError):
        base64_tools.decode_text("not valid !!!")


def test_base64_file_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "data.bin"
    source.write_bytes(bytes(range(32)))
    service = CryptoService(AppSettings())
    encoded = service.base64_encode_file(source)
    restored = service.base64_decode_file(encoded.output_path)
    assert restored.output_path.read_bytes() == bytes(range(32))


def test_base64_file_decode_handles_whitespace_inside_streaming_block(tmp_path: Path) -> None:
    plaintext = bytes(range(251)) * 3_300
    encoded = base64.b64encode(plaintext)
    assert len(encoded) > 1024 * 1024
    wrapped = encoded[:101] + b"\r\n" + encoded[101:]
    source = tmp_path / "stream-boundary.b64"
    source.write_bytes(wrapped)

    result = CryptoService(AppSettings()).base64_decode_file(source)

    assert result.output_path.read_bytes() == plaintext


def test_unique_path_and_output_naming(tmp_path: Path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x", encoding="utf-8")
    first = encrypted_output_path(source)
    first.write_text("existing", encoding="utf-8")
    assert encrypted_output_path(source).name == "report (1).txt.agv"
    assert decrypted_output_path(first).name == "report (1).txt"
    assert unique_path(source).name == "report (1).txt"


@pytest.mark.parametrize(
    ("name", "numbered"),
    [
        ("archive.tar.gz", "archive (1).tar.gz.b64"),
        (".env", ".env (1).b64"),
        ("README", "README (1).b64"),
        ("report (1).txt", "report (1) (1).txt.b64"),
        ("报告.数据.txt", "报告 (1).数据.txt.b64"),
    ],
)
def test_wrapped_output_collision_preserves_logical_suffixes(tmp_path: Path, name: str, numbered: str) -> None:
    source = tmp_path / name
    source.write_bytes(b"content")
    first = base64_encoded_output_path(source)
    first.write_bytes(b"occupied")
    assert base64_encoded_output_path(source).name == numbered


@pytest.mark.parametrize("kind", ["base64", "agv1"])
def test_two_wrapped_conflicts_restore_extension_and_bytes(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "report.txt"
    source.write_bytes(b"synthetic report")
    service = CryptoService(AppSettings())
    wrappers = [
        service.base64_encode_file(source) if kind == "base64" else service.encrypt_file(source, "password")
        for _ in range(3)
    ]
    assert [item.output_path.name for item in wrappers] == [
        f"report.txt.{ 'b64' if kind == 'base64' else 'agv' }",
        f"report (1).txt.{ 'b64' if kind == 'base64' else 'agv' }",
        f"report (2).txt.{ 'b64' if kind == 'base64' else 'agv' }",
    ]
    for index, wrapper in enumerate(wrappers[1:], 1):
        destination = tmp_path / f"restored-{index}"
        destination.mkdir()
        restored = (
            service.base64_decode_file(wrapper.output_path, output_dir=destination)
            if kind == "base64"
            else service.decrypt_file(wrapper.output_path, "password", output_dir=destination)
        )
        assert restored.output_path.name == f"report ({index}).txt"
        assert restored.output_path.suffix == ".txt"
        assert restored.output_path.read_bytes() == source.read_bytes()


def test_concurrent_service_publish_never_overwrites_racing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "race.txt"
    source.write_bytes(b"real service payload")
    ready = Barrier(2)
    real_publish = core_file_io._publish_no_overwrite

    def synchronized_publish(temporary: str, destination: Path) -> bool:
        ready.wait(timeout=5)
        return real_publish(temporary, destination)

    monkeypatch.setattr(core_file_io, "_publish_no_overwrite", synchronized_publish)

    def encode() -> tuple[str, str]:
        try:
            result = CryptoService(AppSettings()).base64_encode_file(source)
            return "published", result.output_path.name
        except FileIOError as exc:
            return exc.code, ""

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: encode(), range(2)))

    assert sorted(status for status, _name in outcomes) == ["file.output_exists", "published"]
    assert (tmp_path / "race.txt.b64").read_bytes() == base64.b64encode(source.read_bytes())
    assert not list(tmp_path.glob(".aegisvault-*.tmp"))
