from __future__ import annotations

from pathlib import Path

import pytest

from aegisvault.core.exceptions import ValidationError
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings


def test_encrypt_text_empty_password_fails() -> None:
    with pytest.raises(ValidationError):
        CryptoService(AppSettings()).encrypt_text("secret", "")


def test_decrypt_text_empty_password_fails() -> None:
    with pytest.raises(ValidationError):
        CryptoService(AppSettings()).decrypt_text("AGV1.invalid", "")


def test_encrypt_file_empty_password_fails(tmp_path: Path) -> None:
    source = tmp_path / "plain.txt"
    source.write_text("secret", encoding="utf-8")
    with pytest.raises(ValidationError):
        CryptoService(AppSettings()).encrypt_file(source, "")


def test_decrypt_file_empty_password_fails(tmp_path: Path) -> None:
    source = tmp_path / "cipher.agv"
    source.write_bytes(b"not real")
    with pytest.raises(ValidationError):
        CryptoService(AppSettings()).decrypt_file(source, "")
