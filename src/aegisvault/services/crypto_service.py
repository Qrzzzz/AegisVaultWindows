"""Application service facade for crypto workflows."""

from __future__ import annotations

import os
from pathlib import Path

from aegisvault.core import base64_tools
from aegisvault.core.crypto import decrypt_file, decrypt_text_auto, encrypt_file, encrypt_text, is_modern_file
from aegisvault.core.exceptions import (
    CompatibilityError,
    FileIOError,
    OperationCancelled,
    ValidationError,
)
from aegisvault.core.legacy import LEGACY_FILE_MAX_BYTES, decrypt_legacy_bytes, is_ak_token
from aegisvault.core.models import (
    CancelToken,
    FileProcessResult,
    ProgressCallback,
    ProgressEvent,
    TextDecryptResult,
    TextEncryptResult,
)
from aegisvault.services.file_io import (
    atomic_binary_writer,
    base64_decoded_output_path,
    base64_encoded_output_path,
    decrypted_output_path,
    encrypted_output_path,
    ensure_input_file,
    file_size,
)
from aegisvault.settings.models import AppSettings


class CryptoService:
    """Coordinates output naming, compatibility decisions and core operations."""

    def __init__(self, settings: AppSettings) -> None:
        settings.validate()
        self.settings = settings

    def encrypt_text(self, plaintext: str, password: str) -> TextEncryptResult:
        self._require_password(password)
        return encrypt_text(plaintext, password)

    def decrypt_text(self, ciphertext: str, password: str | None = None) -> TextDecryptResult:
        if is_ak_token(ciphertext.strip()) and not self.settings.allow_ak_compatibility:
            raise CompatibilityError("AK compatibility parsing is disabled.", code="legacy.ak_disabled")
        if not is_ak_token(ciphertext.strip()):
            self._require_password(password)
        return decrypt_text_auto(ciphertext, password, allow_legacy=True)

    def encrypt_file(
        self,
        input_path: Path,
        password: str,
        *,
        output_dir: Path | None = None,
        progress: ProgressCallback | None = None,
        cancel_token: CancelToken | None = None,
    ) -> FileProcessResult:
        self._require_password(password)
        input_path = ensure_input_file(input_path)
        out_dir = self._output_dir(output_dir)
        output_path = encrypted_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
        return encrypt_file(
            input_path,
            output_path,
            password,
            overwrite=self.settings.overwrite_outputs,
            progress=progress,
            cancel_token=cancel_token,
        )

    def decrypt_file(
        self,
        input_path: Path,
        password: str,
        *,
        output_dir: Path | None = None,
        progress: ProgressCallback | None = None,
        cancel_token: CancelToken | None = None,
        allow_legacy: bool = True,
    ) -> FileProcessResult:
        """Decrypt a file, retaining the historical auto-legacy fallback.

        New integrations should pass ``allow_legacy=False`` and route confirmed
        recovery requests through :meth:`recover_legacy_file` explicitly.
        """

        self._require_password(password)
        if type(allow_legacy) is not bool:
            raise ValidationError("Invalid legacy recovery option.", code="legacy.invalid_option")
        input_path = ensure_input_file(input_path)
        out_dir = self._output_dir(output_dir)

        if is_modern_file(input_path):
            output_path = decrypted_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
            return decrypt_file(
                input_path,
                output_path,
                password,
                overwrite=self.settings.overwrite_outputs,
                progress=progress,
                cancel_token=cancel_token,
            )

        if not allow_legacy:
            raise CompatibilityError(
                "Legacy file recovery must be requested explicitly.",
                code="legacy.file_recovery_required",
            )
        return self.recover_legacy_file(
            input_path,
            password,
            output_dir=out_dir,
            progress=progress,
            cancel_token=cancel_token,
        )

    def recover_legacy_file(
        self,
        input_path: Path,
        password: str,
        *,
        output_dir: Path | None = None,
        progress: ProgressCallback | None = None,
        cancel_token: CancelToken | None = None,
        max_input_bytes: int | None = None,
    ) -> FileProcessResult:
        """Explicitly recover one legacy raw AES-GCM file within a hard limit."""

        self._require_password(password)
        input_path = ensure_input_file(input_path)
        if is_modern_file(input_path):
            raise CompatibilityError("Modern AGV1 files must use the modern decryptor.", code="legacy.modern_file")
        out_dir = self._output_dir(output_dir)
        output_path = decrypted_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
        limit = self._legacy_recovery_limit(max_input_bytes)
        self._check_cancel(cancel_token)
        self._emit(progress, 0.02, "preparing", input_path.name, processed_bytes=0, total_bytes=None)
        encrypted, original_size = self._read_legacy_file_limited(input_path, limit)
        self._check_cancel(cancel_token)
        plaintext = decrypt_legacy_bytes(encrypted, password)
        self._check_cancel(cancel_token)
        with atomic_binary_writer(output_path, overwrite=self.settings.overwrite_outputs) as target:
            target.write(plaintext)
            self._emit(progress, 1.0, "done", output_path.name, processed_bytes=original_size, total_bytes=original_size)
            self._check_cancel(cancel_token)
        return FileProcessResult(
            input_path,
            output_path,
            original_size,
            len(plaintext),
            "legacy-v2",
            "legacy_weak_kdf",
        )

    def base64_encode_text(self, text: str) -> str:
        return base64_tools.encode_text(text)

    def base64_decode_text(self, text: str, *, strict: bool = True, ignore_ascii_whitespace: bool = False) -> str:
        return base64_tools.decode_text(text, strict=strict, ignore_ascii_whitespace=ignore_ascii_whitespace)

    def base64_encode_file(
        self,
        input_path: Path,
        *,
        output_dir: Path | None = None,
        progress: ProgressCallback | None = None,
        cancel_token: CancelToken | None = None,
    ) -> FileProcessResult:
        input_path = ensure_input_file(input_path)
        out_dir = self._output_dir(output_dir)
        output_path = base64_encoded_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
        original_size = file_size(input_path)
        processed = 0
        self._emit(progress, 0.02, "preparing", input_path.name, processed_bytes=0, total_bytes=original_size)
        with input_path.open("rb") as source, atomic_binary_writer(output_path, overwrite=self.settings.overwrite_outputs) as target:
            remainder = b""
            while True:
                self._check_cancel(cancel_token)
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                processed += len(chunk)
                chunk = remainder + chunk
                usable = (len(chunk) // 3) * 3
                if usable:
                    target.write(base64_tools.encode_bytes(chunk[:usable]))
                remainder = chunk[usable:]
                self._emit(
                    progress,
                    0.05 + 0.9 * (processed / max(original_size, 1)),
                    "encoding",
                    input_path.name,
                    processed_bytes=processed,
                    total_bytes=original_size,
                )
            if remainder:
                target.write(base64_tools.encode_bytes(remainder))
            self._check_cancel(cancel_token)
            self._emit(progress, 1.0, "done", output_path.name, processed_bytes=original_size, total_bytes=original_size)
            self._check_cancel(cancel_token)
            output_size = target.tell()
        return FileProcessResult(input_path, output_path, original_size, output_size, "base64")

    def base64_decode_file(
        self,
        input_path: Path,
        *,
        output_dir: Path | None = None,
        progress: ProgressCallback | None = None,
        cancel_token: CancelToken | None = None,
    ) -> FileProcessResult:
        input_path = ensure_input_file(input_path)
        out_dir = self._output_dir(output_dir)
        output_path = base64_decoded_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
        original_size = file_size(input_path)
        processed = 0
        self._emit(progress, 0.02, "preparing", input_path.name, processed_bytes=0, total_bytes=original_size)
        with input_path.open("rb") as source, atomic_binary_writer(output_path, overwrite=self.settings.overwrite_outputs) as target:
            decoder = base64_tools.Base64StreamDecoder(strict=False, ignore_ascii_whitespace=True)
            while True:
                self._check_cancel(cancel_token)
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                processed += len(chunk)
                decoded = decoder.feed(chunk)
                if decoded:
                    target.write(decoded)
                self._emit(
                    progress,
                    0.05 + 0.9 * (processed / max(original_size, 1)),
                    "decoding",
                    input_path.name,
                    processed_bytes=processed,
                    total_bytes=original_size,
                )
            final = decoder.finalize()
            if final:
                target.write(final)
            self._check_cancel(cancel_token)
            self._emit(progress, 1.0, "done", output_path.name, processed_bytes=original_size, total_bytes=original_size)
            self._check_cancel(cancel_token)
            output_size = target.tell()
        return FileProcessResult(input_path, output_path, original_size, output_size, "base64")

    def _output_dir(self, override: Path | None = None) -> Path | None:
        if override:
            return self._validated_output_dir(override)
        if self.settings.default_output_dir:
            return self._validated_output_dir(Path(self.settings.default_output_dir))
        return None

    def _validated_output_dir(self, value: Path) -> Path:
        directory = value.expanduser().resolve()
        if not directory.exists() or not directory.is_dir():
            raise FileIOError(f"Output directory is not available: {directory}", code="file.output_dir_invalid")
        return directory

    def _legacy_recovery_limit(self, requested: int | None) -> int:
        if requested is None:
            return LEGACY_FILE_MAX_BYTES
        if type(requested) is not int or not (1 <= requested <= LEGACY_FILE_MAX_BYTES):
            raise ValidationError("Invalid legacy recovery size limit.", code="legacy.invalid_limit")
        return requested

    def _read_legacy_file_limited(self, path: Path, limit: int) -> tuple[bytes, int]:
        try:
            with path.open("rb") as source:
                before = os.fstat(source.fileno())
                if before.st_size > limit:
                    self._raise_legacy_file_too_large()
                data = source.read(limit + 1)
                after = os.fstat(source.fileno())
        except CompatibilityError:
            raise
        except OSError as exc:
            raise FileIOError("Could not read legacy input file.", code="file.read_failed") from exc
        if len(data) > limit:
            self._raise_legacy_file_too_large()
        before_signature = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        after_signature = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if before_signature != after_signature or len(data) != after.st_size:
            raise FileIOError("Legacy input changed while it was being read.", code="file.input_changed")
        return data, len(data)

    def _raise_legacy_file_too_large(self) -> None:
        raise CompatibilityError(
            "Legacy AES-GCM files require authenticated whole-file migration and are too large for safe in-memory recovery.",
            code="legacy.file_too_large",
        )

    def _emit(
        self,
        progress: ProgressCallback | None,
        percent: float,
        stage: str,
        detail: str = "",
        *,
        processed_bytes: int | None = None,
        total_bytes: int | None = None,
    ) -> None:
        if progress:
            progress(ProgressEvent(max(0.0, min(1.0, percent)), stage, detail, processed_bytes, total_bytes))

    def _check_cancel(self, cancel_token: CancelToken | None) -> None:
        if cancel_token and cancel_token.cancelled:
            raise OperationCancelled("Operation was cancelled.", code="operation.cancelled")

    def _require_password(self, password: str | None) -> None:
        if not isinstance(password, str) or password == "":
            raise ValidationError("Password is required.", code="validation.password_required")
