"""UTF-8 JSON Lines service. stdout contains protocol messages only.

One operation runs at a time. The input reader remains available for cancellation;
EOF cancels and joins the worker so atomic writers can clean up before exit.
Passwords and data are never accepted as command-line arguments or logged.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import Any, BinaryIO

from aegisvault.core.exceptions import AppError, OperationCancelled, ValidationError
from aegisvault.core.models import CancelToken, ProgressCallback
from aegisvault.resource_limits import MAX_JSON_LINE_BYTES, TEXT_LIMITS
from aegisvault.services.batch_service import MAX_BATCH_FILES, process_files
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from aegisvault.version import PACKAGE_VERSION

PROTOCOL_VERSION = 1
MAX_LINE_BYTES = MAX_JSON_LINE_BYTES
OPERATIONS = (
    "hello", "settings.get", "settings.update", "recent.add", "recent.clear",
    "text.encrypt", "text.decrypt", "file.encrypt", "file.decrypt",
    "base64.encode_text", "base64.decode_text", "base64.encode_file", "base64.decode_file",
    "file.batch",
)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate member")
        result[key] = value
    return result


def _string(args: dict[str, Any], name: str, default: str | None = None) -> str:
    value = args.get(name, default)
    if not isinstance(value, str) or (name.endswith("path") or name == "output_dir") and "\0" in value:
        raise ValidationError(code="ipc.invalid_request")
    return value


def _boolean(args: dict[str, Any], name: str, default: bool) -> bool:
    value = args.get(name, default)
    if type(value) is not bool:
        raise ValidationError(code="ipc.invalid_request")
    return value


def _request_id(value: object) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise ValueError()
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError() from exc
    return value


class BackendServer:
    def __init__(self, source: BinaryIO, target: BinaryIO, store: SettingsStore | None = None) -> None:
        self.source, self.target = source, target
        self.store = store or SettingsStore()
        self._write_lock = Lock()
        self._worker: Thread | None = None
        self._token = CancelToken()
        self._active_id: str | None = None

    def emit(self, request_id: str | None, kind: str, **payload: Any) -> None:
        message = {"v": PROTOCOL_VERSION, "id": request_id, "type": kind, **payload}
        raw = (json.dumps(message, ensure_ascii=False, allow_nan=False, default=str) + "\n").encode("utf-8")
        if len(raw) > MAX_LINE_BYTES:
            raise ValidationError("Response exceeds the JSON Line limit.", code="resource.limit_exceeded")
        with self._write_lock:
            self.target.write(raw)
            self.target.flush()

    def run(self) -> int:
        try:
            while raw := self.source.readline(MAX_LINE_BYTES + 1):
                request_id = None
                try:
                    if len(raw) > MAX_LINE_BYTES:
                        self.emit(None, "error", code="ipc.request_too_large")
                        return 2  # Do not interpret a remainder as a new request.
                    request = json.loads(raw.decode("utf-8"), object_pairs_hook=_object,
                                         parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    if not isinstance(request, dict):
                        raise ValueError()
                    try:
                        request_id = _request_id(request.get("id"))
                    except ValueError:
                        request_id = None
                        raise ValueError() from None
                    if type(request.get("v")) is not int or request["v"] != PROTOCOL_VERSION:
                        self.emit(request_id, "error", code="ipc.unsupported_version")
                        continue
                    op = request.get("op")
                    args = request.get("args", {})
                    if not isinstance(op, str) or not isinstance(args, dict):
                        raise ValueError()
                    if op == "cancel":
                        if request_id == self._active_id and self._worker and self._worker.is_alive():
                            self._token.cancel()
                        continue  # The original operation emits exactly one terminal event.
                    if op not in OPERATIONS:
                        self.emit(request_id, "error", code="ipc.unknown_operation")
                        continue
                    if self._worker and self._worker.is_alive():
                        self.emit(request_id, "error", code="ipc.busy")
                        continue
                    self._active_id = request_id
                    self._token = CancelToken()
                    self._worker = Thread(target=self._execute, args=(request_id, op, args), daemon=False)
                    self._worker.start()
                except (ValueError, UnicodeError, RecursionError):
                    self.emit(request_id, "error", code="ipc.invalid_request")
        except (BrokenPipeError, OSError):
            return 1
        finally:
            self._token.cancel()
            if self._worker:
                self._worker.join()
        return 0

    def _execute(self, request_id: str, op: str, args: dict[str, Any]) -> None:
        try:
            result = self.dispatch(op, args, lambda event: self.emit(request_id, "progress", **asdict(event)))
            if is_dataclass(result) and not isinstance(result, type):
                result = asdict(result)
            self.emit(request_id, "result", result=result)
        except OperationCancelled:
            self.emit(request_id, "cancelled", code="operation.cancelled")
        except AppError as exc:
            self.emit(request_id, "error", code=exc.code)
        except (OSError, ValueError):
            self.emit(request_id, "error", code="file.io_error")
        except Exception:
            self.emit(request_id, "error", code="app.error")

    def dispatch(self, op: str, args: dict[str, Any], progress: ProgressCallback) -> Any:
        if op == "hello":
            return {"protocol": PROTOCOL_VERSION, "version": PACKAGE_VERSION, "operations": OPERATIONS,
                    "max_line_bytes": MAX_LINE_BYTES, "text_limits": TEXT_LIMITS.to_dict(),
                    "max_batch_files": MAX_BATCH_FILES}
        if op in {"settings.update", "recent.add", "recent.clear"}:
            return self.store.update(
                lambda settings: self._change_settings(settings, op, args), cancel_token=self._token
            ).to_dict()
        settings = self.store.load()
        if op == "settings.get":
            return settings.to_dict()
        service = CryptoService(settings)
        if self._token.cancelled:
            raise OperationCancelled()
        if op == "file.batch":
            paths = args.get("input_paths")
            if not isinstance(paths, list):
                raise ValidationError(code="ipc.invalid_request")
            destination = _string(args, "output_dir", "")
            return process_files(settings, _string(args, "operation"), paths,
                                 password=_string(args, "password", ""),
                                 output_dir=Path(destination) if destination else None,
                                 progress=progress, cancel_token=self._token)
        if op == "text.encrypt":
            return service.encrypt_text(_string(args, "text"), _string(args, "password"))
        if op == "text.decrypt":
            return service.decrypt_text(_string(args, "text"), _string(args, "password"))
        if op == "base64.encode_text":
            return {"text": service.base64_encode_text(_string(args, "text"))}
        if op == "base64.decode_text":
            return {"text": service.base64_decode_text(
                _string(args, "text"), strict=_boolean(args, "strict", True),
                ignore_ascii_whitespace=_boolean(args, "ignore_ascii_whitespace", False))}
        path = Path(_string(args, "input_path"))
        output_dir = _string(args, "output_dir", "")
        kwargs: dict[str, Any] = {"output_dir": Path(output_dir) if output_dir else None,
                  "progress": progress, "cancel_token": self._token}
        if op == "file.encrypt":
            return service.encrypt_file(path, _string(args, "password"), **kwargs)
        if op == "file.decrypt":
            return service.decrypt_file(path, _string(args, "password"), **kwargs)
        if op == "base64.encode_file":
            return service.base64_encode_file(path, **kwargs)
        if op == "base64.decode_file":
            return service.base64_decode_file(path, **kwargs)
        raise ValidationError(code="ipc.unknown_operation")

    def _change_settings(self, settings: AppSettings, op: str, args: dict[str, Any]) -> AppSettings:
        if op == "settings.update":
            allowed = set(settings.to_dict()) - {"recent_files"}
            if set(args) - allowed:
                raise ValidationError(code="ipc.invalid_request")
            candidate = AppSettings(**(settings.to_dict() | args))
            candidate.validate()
            if candidate.default_output_dir:
                CryptoService(candidate)._output_dir()
            if not candidate.remember_recent_files:
                candidate.recent_files = []
            return candidate
        if op in {"recent.add", "recent.clear"}:
            if op == "recent.clear":
                settings.recent_files = []
            elif settings.remember_recent_files:
                recent_path = str(Path(_string(args, "input_path")).resolve())
                settings.recent_files = ([recent_path] + [p for p in settings.recent_files if p != recent_path])[:12]
            return settings
        raise ValidationError(code="ipc.unknown_operation")


def main() -> int:
    if len(sys.argv) != 1:
        return 2  # No data, password, interpreter switch or operation in argv.
    return BackendServer(sys.stdin.buffer, sys.stdout.buffer).run()


if __name__ == "__main__":
    raise SystemExit(main())
