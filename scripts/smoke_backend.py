"""Exercise the shipped JSONL executable with an isolated profile and minimal PATH."""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import tempfile
import threading
from pathlib import Path

from release_metadata import load_release_metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="aegisvault-smoke-") as directory:
        environment = os.environ | {"LOCALAPPDATA": directory, "APPDATA": directory,
                                    "PATH": os.path.join(os.environ["SYSTEMROOT"], "System32"), "PYTHONUTF8": "1"}
        environment.pop("PYTHONPATH", None)
        with subprocess.Popen([str(args.executable.resolve())], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=directory, env=environment) as process:
            assert process.stdin and process.stdout
            events: queue.Queue[bytes] = queue.Queue()
            def reader() -> None:
                assert process.stdout
                for line in process.stdout:
                    events.put(line)
            threading.Thread(target=reader, daemon=True).start()
            def call(op: str, data: dict | None = None) -> dict:
                assert process.stdin
                process.stdin.write((json.dumps({"v": 1, "id": "smoke", "op": op, "args": data or {}}) + "\n").encode())
                process.stdin.flush()
                while True:
                    result = json.loads(events.get(timeout=30))
                    if result["type"] == "progress":
                        continue
                    assert result["type"] == "result", result
                    return result["result"]
            try:
                assert call("hello")["version"] == load_release_metadata()["version"]
                encrypted = call("text.encrypt", {"text": "WinUI 验收 🔐", "password": "smoke-password"})
                decrypted = call("text.decrypt", {"text": encrypted["ciphertext"], "password": "smoke-password"})
                assert decrypted["plaintext"] == "WinUI 验收 🔐"
                source = Path(directory) / "input.bin"
                source.write_bytes(bytes(range(256)) * 1024)
                result = call("file.encrypt", {"input_path": str(source), "password": "smoke-password"})
                output = call("file.decrypt", {"input_path": result["output_path"], "password": "smoke-password"})
                assert Path(output["output_path"]).read_bytes() == source.read_bytes()
                assert call("base64.decode_text", {"text": "aGVsbG8="})["text"] == "hello"
                process.stdin.close()
                assert process.wait(timeout=15) == 0
            finally:
                if process.poll() is None:
                    process.kill()
    print("Packaged backend smoke passed: hello, AGV1 text/file, Base64; isolated profile and PATH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
