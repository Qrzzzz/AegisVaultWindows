from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from aegisvault.core.crypto import decrypt_file, decrypt_text, encrypt_file, encrypt_text
from aegisvault.core.exceptions import ResourceLimitError
from aegisvault.core.kdf import ScryptParams
from aegisvault.resource_limits import TEXT_LIMITS
from test_backend_protocol import Client

FIXTURE = json.loads((Path(__file__).parent / "fixtures/agv1-passwords.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["name"])
def test_genuine_29_long_password_tokens_remain_decryptable(case: dict) -> None:
    assert FIXTURE["writer_version"] == "2.9"
    assert decrypt_text(case["token"], case["password_base"] * case["repeat"]).plaintext == case["plaintext"]


def test_genuine_29_file_password_above_new_encryption_budget_remains_decryptable(tmp_path: Path) -> None:
    case = FIXTURE["file"]
    encrypted, restored = tmp_path / "legacy.agv", tmp_path / "restored.bin"
    encrypted.write_bytes(base64.b64decode(case["container_base64"]))
    decrypt_file(encrypted, restored, case["password_base"] * case["repeat"])
    assert restored.read_bytes() == base64.b64decode(case["plaintext_base64"])


@pytest.mark.parametrize("character,repeat", [("p", 32768), ("你", 32768), ("🔐", 16384)])
def test_new_encryption_accepts_utf16_boundary_and_rejects_next_unit(character: str, repeat: int, tmp_path: Path) -> None:
    password = character * repeat
    assert len(password.encode("utf-16-le")) // 2 == TEXT_LIMITS.max_encryption_password_utf16_code_units
    token = encrypt_text("shared boundary", password, kdf_params=ScryptParams(salt=b"b" * 16, n=2**14)).ciphertext
    assert decrypt_text(token, password).plaintext == "shared boundary"
    with pytest.raises(ResourceLimitError) as text_error:
        encrypt_text("must not encrypt", password + "x")
    source, output = tmp_path / "source", tmp_path / "source.agv"
    source.write_bytes(b"must stay untouched")
    with pytest.raises(ResourceLimitError) as file_error:
        encrypt_file(source, output, password + "x")
    assert text_error.value.code == file_error.value.code == "resource.password_too_large"
    assert not output.exists()
    assert not list(tmp_path.glob(".aegisvault-*.tmp"))


def test_real_backend_rejects_new_over_budget_password_and_decrypts_legacy(tmp_path: Path) -> None:
    client = Client(tmp_path)
    password = "p" * (TEXT_LIMITS.max_encryption_password_utf16_code_units + 1)
    try:
        client.send("text.encrypt", {"text": "blocked", "password": password})
        terminal, _ = client.terminal()
        assert terminal["type"] == "error" and terminal["code"] == "resource.password_too_large"
        case = FIXTURE["cases"][-1]
        client.send("text.decrypt", {"text": case["token"], "password": password}, request_id="legacy")
        terminal, _ = client.terminal()
        assert terminal["type"] == "result" and terminal["result"]["plaintext"] == case["plaintext"]
    finally:
        client.close()
