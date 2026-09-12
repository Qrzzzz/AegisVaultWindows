from __future__ import annotations

import base64
from pathlib import Path

import pytest

from aegisvault.core.crypto import encrypt_file
from test_backend_protocol import Client


def rpc(root: Path, op: str, args: dict) -> dict:
    client = Client(root)
    try:
        client.send(op, args)
        return client.terminal()[0]
    finally:
        client.close()


@pytest.mark.parametrize("kind", ["base64", "agv1"])
@pytest.mark.parametrize("logical_name", ["", ".", "..", " ", "...", "report.txt", ".env"])
@pytest.mark.parametrize("directory_source", ["explicit", "settings", "input"])
def test_restore_output_stays_in_selected_directory(tmp_path: Path, kind: str, logical_name: str,
                                                   directory_source: str) -> None:
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    selected = incoming if directory_source == "input" else tmp_path / "selected"
    selected.mkdir(exist_ok=True)
    plaintext = tmp_path / "payload.txt"
    payload = b"synthetic\r\nrestored bytes\x00"
    plaintext.write_bytes(payload)
    wrapped = incoming / (logical_name + (".b64" if kind == "base64" else ".agv"))
    if kind == "base64":
        wrapped.write_bytes(base64.b64encode(payload))
    else:
        encrypt_file(plaintext, wrapped, "synthetic-password")
    original = wrapped.read_bytes()
    if directory_source == "settings":
        assert rpc(tmp_path, "settings.update", {"default_output_dir": str(selected)})["type"] == "result"
    args = {"input_path": str(wrapped), "password": "synthetic-password"}
    if directory_source == "explicit":
        args["output_dir"] = str(selected)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    event = rpc(tmp_path, "base64.decode_file" if kind == "base64" else "file.decrypt", args)
    if not logical_name.rstrip(". "):
        assert event["type"] == "error", event
        assert event["code"] == "file.output_name_invalid"
        assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    else:
        assert event["type"] == "result", event
        result = Path(event["result"]["output_path"])
        assert result.parent.resolve() == selected.resolve()
        assert result.is_file() and result.read_bytes() == payload
        again = rpc(tmp_path, "base64.decode_file" if kind == "base64" else "file.decrypt", args)
        sibling = Path(again["result"]["output_path"])
        assert sibling != result and sibling.parent.resolve() == selected.resolve()
        assert sibling.read_bytes() == result.read_bytes() == payload
    assert wrapped.read_bytes() == original
    assert plaintext.read_bytes() == payload
    assert not list(tmp_path.rglob(".aegisvault-*.tmp"))
