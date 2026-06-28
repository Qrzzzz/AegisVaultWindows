from __future__ import annotations

from pathlib import Path

import pytest

from aegisvault.core import base64_tools
from aegisvault.core.exceptions import ValidationError
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import decrypted_output_path, encrypted_output_path, unique_path
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


def test_unique_path_and_output_naming(tmp_path: Path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x", encoding="utf-8")
    first = encrypted_output_path(source)
    first.write_text("existing", encoding="utf-8")
    assert encrypted_output_path(source).name == "report.txt (1).agv"
    assert decrypted_output_path(first).name == "report (1).txt"
    assert unique_path(source).name == "report (1).txt"

