from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from io import BytesIO
from pathlib import Path

import pytest

import aegisvault.core.file_io as file_io
from aegisvault.backend.server import BackendServer
from aegisvault.core.exceptions import FileIOError, OperationCancelled
from aegisvault.core.models import CancelToken
from aegisvault.services.recent_files import RecentFilesService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from test_backend_protocol import Client

ROOT = Path(__file__).resolve().parents[1]


class Worker:
    def __init__(self, path: Path, op: str, args: dict, *, pause: bool = False):
        bootstrap = (f"import sys, runpy; sys.path.insert(0, {str(ROOT / 'src')!r}); "
                     f"runpy.run_path({str(ROOT / 'tests/settings_process_worker.py')!r}, run_name='__main__')")
        self.process = subprocess.Popen([sys.executable, "-I", "-c", bootstrap], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.events: queue.Queue[dict] = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.send(json.dumps({"path": str(path), "op": op, "args": args, "pause": pause}))

    def _read(self):
        for line in self.process.stdout:
            self.events.put(json.loads(line))

    def send(self, value: str):
        self.process.stdin.write((value + "\n").encode())
        self.process.stdin.flush()

    def expect(self, event: str) -> dict:
        value = self.events.get(timeout=10)
        assert value["event"] == event, value
        return value

    def finish(self) -> dict:
        result = self.expect("result")["settings"]
        assert self.process.wait(timeout=10) == 0
        assert self.process.stderr.read() == b""
        return result

    def __enter__(self):
        return self

    def __exit__(self, *_):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()


@pytest.mark.parametrize("first,second,expected", [
    (("settings.update", {"remember_recent_files": False}), ("recent.add", {"input_path": "synthetic.txt"}),
     {"remember_recent_files": False, "recent_files": []}),
    (("recent.add", {"input_path": "synthetic.txt"}), ("settings.update", {"remember_recent_files": False}),
     {"remember_recent_files": False, "recent_files": []}),
    (("settings.update", {"theme": "dark"}), ("settings.update", {"language": "en-US"}),
     {"theme": "dark", "language": "en-US"}),
    (("recent.clear", {}), ("settings.update", {"theme": "dark"}), {"recent_files": [], "theme": "dark"}),
    (("settings.update", {"theme": "dark"}), ("recent.clear", {}), {"recent_files": [], "theme": "dark"}),
])
def test_process_transactions_serialize_before_loading(tmp_path: Path, first: tuple, second: tuple, expected: dict) -> None:
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save(AppSettings(show_advanced_options=True, recent_files=["old-synthetic.txt"]))
    with Worker(path, *first, pause=True) as a:
        a.expect("started")
        a.expect("loaded")
        with Worker(path, *second) as b:
            b.expect("started")
            # The second process waits before load, not at a barrier inside a
            # second transaction. A save-only lock fails this assertion.
            b.expect("contended")
            a.send("go")
            saved_first = a.finish()
            if first[1].get("remember_recent_files") is False:
                assert saved_first["remember_recent_files"] is False
                assert store.load().remember_recent_files is False
            loaded_second = b.expect("loaded")["settings"]
            assert loaded_second == saved_first
            saved_second = b.finish()
    actual = store.load().to_dict()
    assert actual == saved_second
    for key, value in expected.items():
        assert actual[key] == value
    assert actual["show_advanced_options"] is True
    assert not list(tmp_path.glob(".*.tmp"))


def test_write_failure_preserves_snapshot_and_releases_transaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(AppSettings(recent_files=["synthetic.txt"]))
    original = store.path.read_bytes()
    server = BackendServer(BytesIO(), BytesIO(), store)

    def fail_replace(*_):
        raise OSError("injected atomic replace failure")

    with monkeypatch.context() as patch:
        patch.setattr(file_io.os, "replace", fail_replace)
        with pytest.raises(FileIOError) as caught:
            server.dispatch("settings.update", {"theme": "dark"}, lambda _: None)
        assert caught.value.code == "file.write_failed"
    assert store.path.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp"))
    with Worker(store.path, "recent.clear", {}) as worker:
        worker.expect("started")
        worker.expect("loaded")
        assert worker.finish()["recent_files"] == []


def test_real_backend_timeout_is_bounded_and_reads_remain_available(tmp_path: Path) -> None:
    path = tmp_path / "AegisVault/settings.json"
    store = SettingsStore(path)
    store.save(AppSettings())
    with Worker(path, "settings.update", {"theme": "dark"}, pause=True) as holder:
        holder.expect("started")
        holder.expect("loaded")
        client = Client(tmp_path)
        try:
            start = time.monotonic()
            client.send("settings.update", {"language": "en-US"})
            assert client.receive() == {"v": 1, "id": "test", "type": "error", "code": "settings.lock_timeout"}
            assert 4.5 <= time.monotonic() - start < 9
            client.send("settings.get")
            assert client.receive()["result"] == AppSettings().to_dict()
            client.send("base64.encode_text", {"text": "abc"})
            assert client.receive()["result"]["text"] == "YWJj"
            source = tmp_path / "synthetic.bin"
            source.write_bytes(b"abc" * 4096)
            client.send("base64.encode_file", {"input_path": str(source)})
            event, _ = client.terminal()
            assert event["type"] == "result"
            assert Path(event["result"]["output_path"]).read_bytes() == b"YWJj" * 4096
            holder.send("go")
            holder.finish()
            client.send("settings.update", {"language": "en-US"})
            result = client.receive()["result"]
            assert result["theme"] == "dark" and result["language"] == "en-US"
        finally:
            client.close()


@pytest.mark.parametrize("stop", ["exit", "cancel", "exception"])
def test_owner_or_waiter_interruption_cannot_leave_a_permanent_lock(tmp_path: Path, stop: str) -> None:
    path = tmp_path / "settings.json"
    store = SettingsStore(path, lock_timeout=0.2)
    store.save(AppSettings())
    if stop == "exception":
        def fail(_):
            raise RuntimeError("change failed")
        with pytest.raises(RuntimeError, match="change failed"):
            store.update(fail)
    else:
        with Worker(path, "settings.update", {"remember_recent_files": False}, pause=True) as holder:
            holder.expect("started")
            holder.expect("loaded")
            if stop == "cancel":
                token = CancelToken()
                timer = threading.Timer(0.05, token.cancel)
                timer.start()
                try:
                    with pytest.raises(OperationCancelled):
                        store.update(lambda value: value, cancel_token=token)
                finally:
                    timer.join(timeout=2)
            else:
                with pytest.raises(FileIOError) as caught:
                    store.update(lambda value: value)
                assert caught.value.code == "settings.lock_timeout"
            holder.process.kill()
            holder.process.wait(timeout=5)
    assert store.load() == AppSettings()
    # A fresh process acquires the same persistent sidecar after all exits.
    with Worker(path, "settings.update", {"theme": "dark"}) as worker:
        worker.expect("started")
        worker.expect("loaded")
        assert worker.finish()["theme"] == "dark"
    assert not list(tmp_path.glob(".*.tmp"))


@pytest.mark.parametrize("operation", ["add", "clear"])
def test_recent_service_ignores_its_stale_snapshot(tmp_path: Path, operation: str) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(AppSettings())
    service = RecentFilesService(store.load(), store)
    server = BackendServer(BytesIO(), BytesIO(), store)
    server.dispatch("settings.update", {"remember_recent_files": False, "show_advanced_options": True}, lambda _: None)
    service.add(tmp_path / "synthetic.txt") if operation == "add" else service.clear()
    assert store.load().remember_recent_files is False
    assert store.load().recent_files == []
    assert store.load().show_advanced_options is True


def test_lock_failure_is_localized_and_does_not_change_settings(tmp_path: Path) -> None:
    path = tmp_path / "AegisVault/settings.json"
    store = SettingsStore(path)
    store.save(AppSettings())
    path.with_name(".settings.json.lock").mkdir()  # Deterministic Windows open failure.
    with ExitStack() as cleanup:
        client = Client(tmp_path)
        cleanup.callback(client.close)
        client.send("recent.clear")
        event = client.receive()
        assert event["type"] == "error" and event["code"] == "settings.lock_failed"
    assert store.load() == AppSettings()
    for language in ["en-US", "zh-CN"]:
        messages = json.loads((ROOT / f"src/AegisVault.App/Assets/{language}.json").read_text("utf-8"))
        assert messages["error." + event["code"]]
        assert messages["error.settings.lock_timeout"]


def test_explicit_stale_client_fields_are_last_writer_wins(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    server = BackendServer(BytesIO(), BytesIO(), store)
    draft = AppSettings().to_dict()
    draft.pop("recent_files")  # All six preferences sent by SettingsService.SaveAsync.
    server.dispatch("settings.update", {"remember_recent_files": False}, lambda _: None)
    draft["theme"] = "dark"
    server.dispatch("settings.update", draft, lambda _: None)
    assert store.load().remember_recent_files is True  # Documented client conflict boundary.
    assert store.load().theme == "dark"


def test_cancel_before_save_rolls_back_and_releases_lock(tmp_path: Path) -> None:
    store = SettingsStore(tmp_path / "settings.json")
    store.save(AppSettings())
    token = CancelToken()

    def cancel_change(value: AppSettings) -> AppSettings:
        value.theme = "dark"
        token.cancel()
        return value

    with pytest.raises(OperationCancelled):
        store.update(cancel_change, cancel_token=token)
    assert store.load() == AppSettings()
    with Worker(store.path, "settings.update", {"language": "en-US"}) as worker:
        worker.expect("started")
        worker.expect("loaded")
        assert worker.finish()["language"] == "en-US"


@pytest.mark.parametrize("stop", ["cancel", "eof"])
def test_backend_cancel_or_eof_while_settings_are_locked(tmp_path: Path, stop: str) -> None:
    store = SettingsStore(tmp_path / "AegisVault/settings.json")
    store.save(AppSettings())
    with Worker(store.path, "settings.update", {"theme": "dark"}, pause=True) as holder:
        holder.expect("started")
        holder.expect("loaded")
        client = Client(tmp_path)
        start = time.monotonic()
        client.send("settings.update", {"language": "en-US"})
        if stop == "cancel":
            try:
                client.send("cancel")
                assert client.receive()["type"] == "cancelled"
            finally:
                client.close()
        else:
            client.close()
            assert client.receive()["type"] == "cancelled"
        assert time.monotonic() - start < 3
        assert store.load() == AppSettings()
        holder.send("go")
        holder.finish()
    client = Client(tmp_path)
    try:
        client.send("settings.update", {"language": "en-US"})
        result = client.receive()["result"]
        assert result["theme"] == "dark" and result["language"] == "en-US"
    finally:
        client.close()
