"""Exercise the shipped JSONL executable with an isolated profile and minimal PATH."""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path

from release_metadata import load_release_metadata


def _stop_backend(process: subprocess.Popen, reader: threading.Thread, timeout: float) -> None:
    # A one-file PyInstaller bootloader owns a child process. Close its input before
    # waiting, and terminate the whole tree if EOF does not stop it. Killing only
    # the bootloader can leave the reader blocked on a pipe held by its child.
    if process.stdin and not process.stdin.closed:
        with suppress(OSError):
            process.stdin.close()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                [os.path.join(os.environ["SYSTEMROOT"], "System32", "taskkill.exe"),
                 "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                check=False, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        if process.poll() is None:
            process.kill()
        process.wait(timeout=timeout)
    reader.join(timeout=timeout)
    if reader.is_alive():
        raise RuntimeError("Packaged backend retained its output pipe after shutdown")
    if process.stdout:
        process.stdout.close()


def _call_backend(command: list[str], directory: str, op: str, data: dict | None, *,
                  request_timeout: float, shutdown_timeout: float) -> dict:
    environment = os.environ | {"LOCALAPPDATA": directory, "APPDATA": directory,
                                    "PATH": os.path.join(os.environ["SYSTEMROOT"], "System32"), "PYTHONUTF8": "1"}
    environment.pop("PYTHONPATH", None)
    # A file cannot fill a stderr pipe while the main thread waits for a result.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=errors, cwd=directory, env=environment)
        assert process.stdin and process.stdout
        events: queue.Queue[bytes | None] = queue.Queue()

        def read_output() -> None:
            assert process.stdout
            try:
                for line in process.stdout:
                    events.put(line)
            finally:
                events.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()

        def request_result() -> dict:
            assert process.stdin
            print(f"Packaged backend smoke: {op}", flush=True)
            process.stdin.write((json.dumps({"v": 1, "id": "smoke", "op": op, "args": data or {}}) + "\n").encode())
            process.stdin.flush()
            deadline = time.monotonic() + request_timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Packaged backend timed out during {op}")
                try:
                    line = events.get(timeout=remaining)
                except queue.Empty as exc:
                    raise TimeoutError(f"Packaged backend timed out during {op}") from exc
                if line is None:
                    raise RuntimeError(f"Packaged backend closed stdout during {op}")
                result = json.loads(line)
                if result["type"] == "progress":
                    continue
                if result["type"] != "result":
                    raise RuntimeError(f"Packaged backend {op} failed: {result.get('code', result['type'])}")
                return result["result"]

        try:
            result = request_result()
            process.stdin.close()
            assert process.wait(timeout=shutdown_timeout) == 0
            return result
        except BaseException as exc:
            print(f"Packaged backend smoke failed: {exc}", file=sys.stderr, flush=True)
            errors.seek(0)
            detail = errors.read(4096).decode("utf-8", errors="replace")
            if detail:
                print(detail, file=sys.stderr, flush=True)
            raise
        finally:
            _stop_backend(process, reader, shutdown_timeout)


def smoke_backend(command: list[str], directory: str, expected_version: str, *,
                  request_timeout: float = 30, shutdown_timeout: float = 15) -> None:
    # Match BackendClient: one operation per process, and await shutdown before
    # the next call. A terminal event can precede the worker thread's exit.
    def call(op: str, data: dict | None = None) -> dict:
        return _call_backend(command, directory, op, data,
                             request_timeout=request_timeout, shutdown_timeout=shutdown_timeout)

    assert call("hello")["version"] == expected_version
    encrypted = call("text.encrypt", {"text": "WinUI 验收 🔐", "password": "smoke-password"})
    decrypted = call("text.decrypt", {"text": encrypted["ciphertext"], "password": "smoke-password"})
    assert decrypted["plaintext"] == "WinUI 验收 🔐"
    source = Path(directory) / "input.bin"
    source.write_bytes(bytes(range(256)) * 1024)
    result = call("file.encrypt", {"input_path": str(source), "password": "smoke-password"})
    output = call("file.decrypt", {"input_path": result["output_path"], "password": "smoke-password"})
    assert Path(output["output_path"]).read_bytes() == source.read_bytes()
    assert call("base64.decode_text", {"text": "aGVsbG8="})["text"] == "hello"
    extra = Path(directory) / "second.txt"
    extra.write_bytes(b"batch smoke\r\n")
    batch = call("file.batch", {"operation": "file.encrypt", "input_paths": [str(source), str(extra)], "password": "smoke-password"})
    assert [item["status"] for item in batch["items"]] == ["completed", "completed"]
    restored = call("file.batch", {"operation": "file.decrypt", "input_paths": [item["result"]["output_path"] for item in batch["items"]], "password": "smoke-password"})
    assert [Path(item["result"]["output_path"]).read_bytes() for item in restored["items"]] == [source.read_bytes(), extra.read_bytes()]
    partial = call("file.batch", {"operation": "base64.encode_file", "input_paths": [str(Path(directory) / "missing"), str(extra)]})
    assert [item["status"] for item in partial["items"]] == ["failed", "completed"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    expected_version = load_release_metadata()["version"]
    with tempfile.TemporaryDirectory(prefix="aegisvault-smoke-") as directory:
        smoke_backend([str(args.executable.resolve())], directory, expected_version)
    print("Packaged backend smoke passed: hello, AGV1 text/file, Base64; isolated profile and PATH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
