from __future__ import annotations

import importlib.util
import inspect
from dataclasses import fields
from io import BytesIO
from pathlib import Path

import pytest

import aegisvault
import aegisvault.core.crypto as crypto
import aegisvault.core.exceptions as exceptions
import aegisvault.services.crypto_service as service_module
from aegisvault.core.exceptions import ProtocolError
from aegisvault.core.models import FileProcessResult, TextDecryptResult
from aegisvault.core.protocol import FILE_MAGIC, read_file_header
from aegisvault.services.crypto_service import CryptoService
from aegisvault.services.file_io import decrypted_output_path
from aegisvault.settings.models import AppSettings

# Opaque static examples of the removed input shapes, not ciphertext producers.
# No test contains or calls a legacy KDF, encryptor, parser, or decryptor.
RAW_NON_AGV1 = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")
BARE_BASE64 = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
AK_TOKEN = "AK#bundled-key#AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
UNSUPPORTED_TEXT = (AK_TOKEN, BARE_BASE64, "AK#incomplete", "", "不是密文 🔐", "AGV0.invalid")
UNSUPPORTED_FILES = (RAW_NON_AGV1, BARE_BASE64.encode(), AK_TOKEN.encode(), b"", b"AGV", b"AGVTEXT\x01")


@pytest.fixture
def forbid_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Unsupported input reached key derivation, AES-GCM or an output writer")

    monkeypatch.setattr(crypto, "derive_key", forbidden)
    monkeypatch.setattr(crypto, "AESGCM", forbidden)
    monkeypatch.setattr(crypto, "atomic_binary_writer", forbidden)
    monkeypatch.setattr(service_module, "atomic_binary_writer", forbidden)


@pytest.mark.usefixtures("forbid_crypto")
@pytest.mark.parametrize("value", UNSUPPORTED_TEXT)
@pytest.mark.parametrize("password", ["explicit-password", ""])
@pytest.mark.parametrize("use_service", [False, True])
def test_non_agv1_text_is_rejected(value: str, password: str, use_service: bool) -> None:
    decrypt = CryptoService(AppSettings()).decrypt_text if use_service else crypto.decrypt_text
    with pytest.raises(ProtocolError) as caught:
        decrypt(" \r\n" + value + "\t ", password)
    assert caught.value.code == "protocol.unsupported_format"


@pytest.mark.usefixtures("forbid_crypto")
@pytest.mark.parametrize("value", UNSUPPORTED_TEXT)
def test_non_agv1_text_without_a_password_is_rejected(value: str) -> None:
    with pytest.raises(ProtocolError) as caught:
        CryptoService(AppSettings()).decrypt_text(value)
    assert caught.value.code == "protocol.unsupported_format"


@pytest.mark.usefixtures("forbid_crypto")
def test_modern_prefix_does_not_make_raw_ciphertext_supported() -> None:
    with pytest.raises(ProtocolError) as caught:
        CryptoService(AppSettings()).decrypt_text("AGV1." + BARE_BASE64, "explicit-password")
    assert caught.value.code == "protocol.unsupported_format"


@pytest.mark.usefixtures("forbid_crypto")
@pytest.mark.parametrize("data", UNSUPPORTED_FILES)
@pytest.mark.parametrize("use_service", [False, True])
@pytest.mark.parametrize("overwrite", [False, True])
def test_non_agv1_files_leave_inputs_and_outputs_unchanged(
    tmp_path: Path, data: bytes, use_service: bool, overwrite: bool
) -> None:
    source = tmp_path / "旧文件 🔐.aes"
    source.write_bytes(data)
    out_dir = tmp_path / "outputs"
    out_dir.mkdir()
    target = decrypted_output_path(source, out_dir, overwrite=True)
    target.write_bytes(b"existing output must survive")

    with pytest.raises(ProtocolError) as caught:
        if use_service:
            CryptoService(AppSettings(overwrite_outputs=overwrite)).decrypt_file(
                source, "explicit-password", output_dir=out_dir
            )
        else:
            crypto.decrypt_file(source, target, "explicit-password", overwrite=overwrite)

    assert caught.value.code == "protocol.unsupported_format"
    assert source.read_bytes() == data
    assert target.read_bytes() == b"existing output must survive"
    assert list(out_dir.iterdir()) == [target]
    assert set(tmp_path.iterdir()) == {source, out_dir}


@pytest.mark.usefixtures("forbid_crypto")
@pytest.mark.parametrize("use_service", [False, True])
def test_non_agv1_file_with_empty_password_is_still_unsupported(tmp_path: Path, use_service: bool) -> None:
    source = tmp_path / "old.agv"
    source.write_bytes(RAW_NON_AGV1)
    with pytest.raises(ProtocolError) as caught:
        if use_service:
            CryptoService(AppSettings()).decrypt_file(source, "")
        else:
            crypto.decrypt_file(source, tmp_path / "output", "")
    assert caught.value.code == "protocol.unsupported_format"
    assert list(tmp_path.iterdir()) == [source]


def test_non_agv1_file_detection_reads_only_the_magic() -> None:
    class BoundedInput(BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size == len(FILE_MAGIC)
            return super().read(size)

    source = BoundedInput(RAW_NON_AGV1)
    with pytest.raises(ProtocolError) as caught:
        read_file_header(source)
    assert caught.value.code == "protocol.unsupported_format"
    assert source.tell() == len(FILE_MAGIC)


@pytest.mark.parametrize("suffix", [".aes", ".b64"])
def test_decrypted_output_naming_does_not_treat_other_suffixes_as_encryption(suffix: str, tmp_path: Path) -> None:
    source = tmp_path / f"document{suffix}"
    assert decrypted_output_path(source).name == f"document.decrypted{suffix}"


def test_removed_compatibility_apis_are_not_available() -> None:
    assert importlib.util.find_spec("aegisvault.core.legacy") is None
    assert not hasattr(crypto, "decrypt_text_auto")
    assert not hasattr(CryptoService, "recover_legacy_file")
    assert "allow_legacy" not in inspect.signature(CryptoService.decrypt_file).parameters
    assert not hasattr(exceptions, "CompatibilityError")
    assert not hasattr(aegisvault, "__legacy_name__")
    assert "allow_ak_compatibility" not in {field.name for field in fields(AppSettings)}
    assert {field.name for field in fields(TextDecryptResult)} == {"plaintext", "format_name"}
    assert {field.name for field in fields(FileProcessResult)} == {
        "input_path", "output_path", "original_size", "output_size", "format_name"
    }
