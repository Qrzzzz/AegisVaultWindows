from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from io import BytesIO
from pathlib import Path

import pytest

from aegisvault.backend.server import MAX_LINE_BYTES, BackendServer
from aegisvault.settings.store import SettingsStore
from aegisvault.version import DISPLAY_VERSION
from test_protocol_fixtures import FIXED_PASSWORD, FIXED_PLAINTEXT, FIXED_TEXT_TOKEN


class Client:
    def __init__(self, root: Path) -> None:
        environment = os.environ | {"LOCALAPPDATA": str(root), "APPDATA": str(root), "PYTHONUTF8": "1",
                                    "PYTHONPATH": str(Path("src").resolve())}
        self.process = subprocess.Popen([sys.executable, "-m", "aegisvault.backend"], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment)
        self.lines: queue.Queue[bytes] = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        assert self.process.stdout
        for line in self.process.stdout:
            self.lines.put(line)

    def send(self, op: str, args: dict | None = None, *, request_id: str = "test", version: object = 1) -> None:
        self.raw(json.dumps({"v": version, "id": request_id, "op": op, "args": args or {}}, ensure_ascii=False).encode() + b"\n")

    def raw(self, data: bytes) -> None:
        assert self.process.stdin
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def receive(self) -> dict:
        return json.loads(self.lines.get(timeout=15))

    def terminal(self) -> tuple[dict, list[dict]]:
        progress = []
        while True:
            result = self.receive()
            if result["type"] != "progress":
                return result, progress
            progress.append(result)

    def close(self) -> None:
        assert self.process.stdin and self.process.stderr
        self.process.stdin.close()
        try:
            assert self.process.wait(timeout=15) == 0
            assert self.process.stderr.read() == b""
        finally:
            if self.process.poll() is None:
                self.process.kill()
            self.reader.join(timeout=2)


@pytest.fixture
def client(tmp_path: Path):
    instance = Client(tmp_path)
    try:
        yield instance
    finally:
        instance.close()


def test_hello_reports_version_and_no_ui_dependencies(client: Client) -> None:
    client.send("hello")
    event, _ = client.terminal()
    assert event["result"]["protocol"] == 1
    assert event["result"]["version"] == DISPLAY_VERSION
    assert "file.decrypt" in event["result"]["operations"]


def test_ipc_decrypts_1x_fixed_token(client: Client) -> None:
    client.send("text.decrypt", {"text": FIXED_TEXT_TOKEN, "password": FIXED_PASSWORD})
    event, _ = client.terminal()
    assert event["result"]["plaintext"] == FIXED_PLAINTEXT


def test_ipc_text_roundtrip_and_redacted_error(client: Client) -> None:
    client.send("text.encrypt", {"text": "秘密\n🔐", "password": "秘密密码"})
    event, _ = client.terminal()
    ciphertext = event["result"]["ciphertext"]
    client.send("text.decrypt", {"text": ciphertext, "password": "秘密密码"})
    event, _ = client.terminal()
    assert event["result"]["plaintext"] == "秘密\n🔐"
    client.send("text.decrypt", {"text": ciphertext, "password": "wrong-secret"})
    event, _ = client.terminal()
    assert event == {"v": 1, "id": "test", "type": "error", "code": "crypto.authentication_failed"}


@pytest.mark.parametrize("op, code", [("file.invalid", "ipc.unknown_operation"), ("text.encrypt", "ipc.invalid_request")])
def test_bad_requests_do_not_echo_input(client: Client, op: str, code: str) -> None:
    client.send(op, {"text": ["private"]})
    event, _ = client.terminal()
    assert event["type"] == "error" and event["code"] == code
    assert "private" not in json.dumps(event)


@pytest.mark.parametrize("raw", [b'[]\n', b'{"v":1,"v":1,"id":"x"}\n', b'\xff\n', b'{"v":NaN}\n'])
def test_invalid_json_is_recoverable(client: Client, raw: bytes) -> None:
    client.raw(raw)
    assert client.receive()["code"] == "ipc.invalid_request"
    client.send("hello")
    assert client.receive()["type"] == "result"


@pytest.mark.parametrize("version", [True, 2, "1"])
def test_protocol_version_is_strict(client: Client, version: object) -> None:
    client.send("hello", version=version)
    assert client.receive()["code"] == "ipc.unsupported_version"


def test_settings_roundtrip_validation_and_privacy(client: Client, tmp_path: Path) -> None:
    client.send("settings.update", {"language": "en-US", "theme": "dark", "remember_recent_files": False})
    assert client.receive()["result"]["theme"] == "dark"
    client.send("recent.add", {"input_path": str(tmp_path / "private.txt")})
    assert client.receive()["result"]["recent_files"] == []
    client.send("settings.update", {"overwrite_outputs": "false"})
    assert client.receive()["code"] == "settings.invalid_type"
    client.send("settings.get")
    assert client.receive()["result"]["overwrite_outputs"] is False
    assert "private.txt" not in (tmp_path / "AegisVault/settings.json").read_text()


@pytest.mark.parametrize("encode,decode", [("file.encrypt", "file.decrypt"), ("base64.encode_file", "base64.decode_file")])
def test_file_roundtrip_progress_and_atomic_output(client: Client, tmp_path: Path, encode: str, decode: str) -> None:
    path = tmp_path / "样本.bin"
    path.write_bytes(bytes(range(256)) * 8192)
    client.send(encode, {"input_path": str(path), "password": "password"})
    event, progress = client.terminal()
    assert event["type"] == "result"
    assert progress and all(item["id"] == "test" for item in progress)
    assert all(0 <= item["percent"] <= 1 for item in progress)
    encrypted = event["result"]["output_path"]
    client.send(decode, {"input_path": encrypted, "password": "password"})
    event, _ = client.terminal()
    assert Path(event["result"]["output_path"]).read_bytes() == path.read_bytes()
    assert not list(tmp_path.glob(".*.tmp"))


def test_cooperative_cancel_removes_partial_output(client: Client, tmp_path: Path) -> None:
    path = tmp_path / "large.bin"
    with path.open("wb") as handle:
        handle.truncate(64 * 1024 * 1024)
    client.send("file.encrypt", {"input_path": str(path), "password": "password"})
    first = client.receive()
    assert first["type"] == "progress"
    client.send("cancel")
    event, _ = client.terminal()
    assert event["type"] == "cancelled"
    assert set(tmp_path.iterdir()) == {path}


@pytest.mark.parametrize("strict,ignore,text,expected", [(True, False, "Zg==", "f"), (False, True, "Z g==", "f")])
def test_base64_decode_modes(client: Client, strict: bool, ignore: bool, text: str, expected: str) -> None:
    client.send("base64.decode_text", {"text": text, "strict": strict, "ignore_ascii_whitespace": ignore})
    assert client.receive()["result"]["text"] == expected


def test_oversized_frame_stops_without_parsing_remainder(tmp_path: Path) -> None:
    target = BytesIO()
    server = BackendServer(BytesIO(b" " * (MAX_LINE_BYTES + 1) + b'\n{"v":1,"id":"extra","op":"hello"}\n'),
                           target, SettingsStore(tmp_path / "settings.json"))
    assert server.run() == 2
    lines = target.getvalue().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["code"] == "ipc.request_too_large"


def test_eof_cancels_and_joins_file_writer(tmp_path: Path) -> None:
    instance = Client(tmp_path)
    path = tmp_path / "eof.bin"
    with path.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024)
    instance.send("file.encrypt", {"input_path": str(path), "password": "test-password"})
    assert instance.receive()["type"] == "progress"
    instance.close()
    assert set(tmp_path.iterdir()) == {path}


def test_command_line_data_is_rejected() -> None:
    result = subprocess.run([sys.executable, "-m", "aegisvault.backend", "private-password"],
                            capture_output=True, timeout=10)
    assert result.returncode == 2
    assert result.stdout == result.stderr == b""
