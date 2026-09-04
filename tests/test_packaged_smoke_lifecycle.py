from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows packaged-process lifecycle")

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture
def smoke(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("packaged_smoke", SCRIPTS / "smoke_backend.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.smoke_backend


def _bootloader(tmp_path: Path, child_source: str) -> list[str]:
    child_source = (
        "import os, sys, time\nfrom pathlib import Path\n"
        "Path('child.pid').write_text(str(os.getpid()))\n"
        "sys.stdin.readline()\n" + child_source
    )
    launcher = tmp_path / "bootloader.py"
    launcher.write_text(
        "import subprocess, sys\n"
        f"child = subprocess.Popen([sys.executable, '-c', {child_source!r}], "
        "stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)\n"
        "sys.exit(child.wait())\n", encoding="utf-8",
    )
    return [sys.executable, str(launcher)]


def _assert_child_stopped(tmp_path: Path) -> None:
    pid = int((tmp_path / "child.pid").read_text())
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        assert ctypes.get_last_error() == 87  # Process no longer exists.
        return
    try:
        status = wintypes.DWORD()
        assert kernel.GetExitCodeProcess(handle, ctypes.byref(status))
        assert status.value != 259  # STILL_ACTIVE
    finally:
        kernel.CloseHandle(handle)


def test_backend_error_stops_bootloader_child_and_pipe_reader(smoke, tmp_path: Path, capsys) -> None:
    command = _bootloader(tmp_path, "print('{\"type\":\"error\",\"code\":\"synthetic.failure\"}', flush=True)\n"
                          "time.sleep(60)\n")
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="hello failed: synthetic.failure"):
        smoke(command, str(tmp_path), "2.1", request_timeout=5, shutdown_timeout=1)
    assert time.monotonic() - started < 15
    _assert_child_stopped(tmp_path)
    assert "hello failed: synthetic.failure" in capsys.readouterr().err


def test_progress_cannot_extend_request_deadline_or_leave_child(smoke, tmp_path: Path) -> None:
    command = _bootloader(tmp_path, "while True:\n"
                          "    print('{\"type\":\"progress\"}', flush=True)\n"
                          "    time.sleep(0.05)\n")
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="timed out during hello"):
        smoke(command, str(tmp_path), "2.1", request_timeout=3, shutdown_timeout=1)
    assert time.monotonic() - started < 15
    _assert_child_stopped(tmp_path)


def test_stderr_flood_and_early_exit_report_failure_without_pipe_deadlock(smoke, tmp_path: Path, capsys) -> None:
    command = [sys.executable, "-c", "import sys; sys.stderr.write('synthetic stderr ' * 32768)"]
    with pytest.raises(RuntimeError, match="closed stdout during hello"):
        smoke(command, str(tmp_path), "2.1", request_timeout=5, shutdown_timeout=1)
    assert "synthetic stderr" in capsys.readouterr().err


def test_smoke_waits_for_exit_and_starts_each_operation_in_a_fresh_process(smoke, tmp_path: Path) -> None:
    # Keep the real backend worker alive briefly after emitting its terminal
    # event. Reusing that process must deterministically receive ipc.busy.
    launcher = tmp_path / "slow_terminal_backend.py"
    launcher.write_text(
        "import json, os, sys, time\n"
        f"sys.path.insert(0, {str(SCRIPTS.parent / 'src')!r})\n"
        "from aegisvault.backend.server import BackendServer\n"
        "class SlowTerminalBackend(BackendServer):\n"
        "    def dispatch(self, op, args, progress):\n"
        "        with open('operations.jsonl', 'a') as trace:\n"
        "            trace.write(json.dumps({'pid': os.getpid(), 'op': op}) + '\\n')\n"
        "        return super().dispatch(op, args, progress)\n"
        "    def emit(self, request_id, kind, **payload):\n"
        "        super().emit(request_id, kind, **payload)\n"
        "        if kind == 'result':\n"
        "            time.sleep(0.2)\n"
        "raise SystemExit(SlowTerminalBackend(sys.stdin.buffer, sys.stdout.buffer).run())\n",
        encoding="utf-8",
    )
    from aegisvault.version import DISPLAY_VERSION

    smoke([sys.executable, "-I", str(launcher)], str(tmp_path), DISPLAY_VERSION,
          request_timeout=5, shutdown_timeout=3)
    operations = [json.loads(line) for line in (tmp_path / "operations.jsonl").read_text().splitlines()]
    assert [entry["op"] for entry in operations] == [
        "hello", "text.encrypt", "text.decrypt", "file.encrypt", "file.decrypt", "base64.decode_text"
    ]
    assert len({entry["pid"] for entry in operations}) == 6
