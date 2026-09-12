"""Bounded, sequential file batches with independent atomic outputs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

from aegisvault.core.exceptions import AppError, OperationCancelled, ValidationError
from aegisvault.core.models import CancelToken, FileProcessResult, ProgressCallback, ProgressEvent
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings

MAX_BATCH_FILES = 256
MAX_BATCH_PATH_BYTES = 1024 * 1024
FILE_OPERATIONS = ("file.encrypt", "file.decrypt", "base64.encode_file", "base64.decode_file")


@dataclass(frozen=True)
class BatchItemResult:
    input_path: str
    status: str
    result: FileProcessResult | None = None
    code: str = ""


@dataclass(frozen=True)
class BatchResult:
    items: list[BatchItemResult]
    cancelled: bool


def process_files(
    settings: AppSettings,
    operation: str,
    input_paths: list[str],
    *,
    password: str = "",
    output_dir: Path | None = None,
    progress: ProgressCallback | None = None,
    cancel_token: CancelToken | None = None,
) -> BatchResult:
    """Validate the whole request before writes; isolate ordinary per-file failures.

    Batches always choose unused output names, including when a single-file
    overwrite preference is enabled. This protects later inputs and earlier
    outputs in the same batch without changing the single-file API.
    """
    if operation not in FILE_OPERATIONS or not isinstance(input_paths, list) or not input_paths:
        raise ValidationError(code="ipc.invalid_request")
    if len(input_paths) > MAX_BATCH_FILES:
        raise ValidationError(code="resource.limit_exceeded")
    seen: set[str] = set()
    path_bytes = 0
    destination_text = str(output_dir or settings.default_output_dir or "")
    for value in input_paths:
        if not isinstance(value, str) or not value.strip() or "\0" in value or len(value) > 32767:
            raise ValidationError(code="ipc.invalid_request")
        try:
            value.encode("utf-8", errors="strict")
            key = os.path.normcase(str(Path(value).resolve()))
        except (OSError, ValueError, UnicodeError) as exc:
            raise ValidationError(code="ipc.invalid_request") from exc
        if key in seen:
            raise ValidationError(code="validation.duplicate_file")
        seen.add(key)
        # Reserve ample response headroom for repeated paths, output suffixes,
        # status fields and JSON escaping before any output can be committed.
        try:
            path_bytes += len(json.dumps([value, key, destination_text], ensure_ascii=False).encode("utf-8"))
        except UnicodeError as exc:
            raise ValidationError(code="ipc.invalid_request") from exc
        if path_bytes > MAX_BATCH_PATH_BYTES:
            raise ValidationError(code="resource.limit_exceeded")
    if operation.startswith("file."):
        CryptoService(settings)._require_password(password)
    service = CryptoService(replace(settings, overwrite_outputs=False))
    destination = service._output_dir(output_dir)
    items: list[BatchItemResult] = []
    cancelled = False
    count = len(input_paths)
    for index, value in enumerate(input_paths):
        if cancelled or cancel_token and cancel_token.cancelled:
            cancelled = True
            items.append(BatchItemResult(value, "pending"))
            continue

        def report(event: ProgressEvent, position: int = index) -> None:
            if progress:
                progress(replace(event, percent=(position + event.percent) / count))

        try:
            path = Path(value)
            if operation == "file.encrypt":
                result = service.encrypt_file(path, password, output_dir=destination, progress=report, cancel_token=cancel_token)
            elif operation == "file.decrypt":
                result = service.decrypt_file(path, password, output_dir=destination, progress=report, cancel_token=cancel_token)
            elif operation == "base64.encode_file":
                result = service.base64_encode_file(path, output_dir=destination, progress=report, cancel_token=cancel_token)
            else:
                result = service.base64_decode_file(path, output_dir=destination, progress=report, cancel_token=cancel_token)
            items.append(BatchItemResult(value, "completed", result))
        except OperationCancelled:
            cancelled = True
            items.append(BatchItemResult(value, "cancelled", code="operation.cancelled"))
        except AppError as exc:
            items.append(BatchItemResult(value, "failed", code=exc.code))
        except (OSError, ValueError):
            items.append(BatchItemResult(value, "failed", code="file.io_error"))
        if progress:
            progress(ProgressEvent((index + 1) / count, "batch.item_finished", value))
    return BatchResult(items, cancelled)
