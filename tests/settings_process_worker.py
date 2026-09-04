"""Test subprocess with bounded scheduling hooks around real settings operations."""

from __future__ import annotations

import json
import queue
import sys
import threading
from io import BytesIO
from pathlib import Path

import aegisvault.settings.locking as locking
import aegisvault.settings.store as store_module
from aegisvault.backend.server import BackendServer
from aegisvault.settings.store import SettingsStore


def emit(event: str, **values) -> None:
    print(json.dumps({"event": event, **values}), flush=True)


def main() -> None:
    job = json.loads(sys.stdin.readline())
    expected_root = Path(__file__).resolve().parents[1] / "src"
    assert Path(store_module.__file__).resolve().is_relative_to(expected_root)
    real_lock = locking._try_lock
    reported_contention = False

    def observed_lock(handle):
        nonlocal reported_contention
        try:
            real_lock(handle)
        except OSError:
            if not reported_contention:
                emit("contended")
                reported_contention = True
            raise

    locking._try_lock = observed_lock

    class PausedStore(SettingsStore):
        def load(self):
            value = super().load()
            emit("loaded", settings=value.to_dict())
            if job.get("pause"):
                signals: queue.Queue[str] = queue.Queue()
                threading.Thread(target=lambda: signals.put(sys.stdin.readline()), daemon=True).start()
                assert signals.get(timeout=15).strip() == "go", "load barrier not released"
            return value

    server = BackendServer(BytesIO(), BytesIO(), PausedStore(Path(job["path"])))
    emit("started")
    result = server.dispatch(job["op"], job["args"], lambda _: None)
    emit("result", settings=result)


if __name__ == "__main__":
    main()
