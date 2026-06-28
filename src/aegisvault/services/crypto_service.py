"""Application service facade for crypto workflows."""

from __future__ import annotations

from pathlib import Path

from aegisvault.core import base64_tools
from aegisvault.core.crypto import decrypt_file, decrypt_text_auto, encrypt_file, encrypt_text, is_modern_file
from aegisvault.core.exceptions import AuthenticationError, CompatibilityError, FileIOError, OperationCancelled
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
        self.settings = settings

    def encrypt_text(self, plaintext: str, password: str) -> TextEncryptResult:
        return encrypt_text(plaintext, password)

    def decrypt_text(self, ciphertext: str, password: str | None = None) -> TextDecryptResult:
        if is_ak_token(ciphertext.strip()) and not self.settings.allow_ak_compatibility:
            raise CompatibilityError("AK compatibility parsing is disabled.", code="legacy.ak_disabled")
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
    ) -> FileProcessResult:
        input_path = ensure_input_file(input_path)
        out_dir = self._output_dir(output_dir)
        output_path = decrypted_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)

        if is_modern_file(input_path):
            return decrypt_file(
                input_path,
                output_path,
                password,
                overwrite=self.settings.overwrite_outputs,
                progress=progress,
                cancel_token=cancel_token,
            )

        original_size = file_size(input_path)
        if original_size > LEGACY_FILE_MAX_BYTES:
            raise CompatibilityError(
                "Legacy AES-GCM files require authenticated whole-file migration and are too large for safe in-memory recovery.",
                code="legacy.file_too_large",
            )
        if cancel_token and cancel_token.cancelled:
            raise OperationCancelled("Operation was cancelled.", code="operation.cancelled")
        try:
            plaintext = decrypt_legacy_bytes(input_path.read_bytes(), password)
        except AuthenticationError:
            raise
        with atomic_binary_writer(output_path, overwrite=self.settings.overwrite_outputs) as target:
            target.write(plaintext)
        return FileProcessResult(
            input_path,
            output_path,
            original_size,
            file_size(output_path),
            "legacy-v2",
            "legacy_weak_kdf",
        )

    def base64_encode_text(self, text: str) -> str:
        return base64_tools.encode_text(text)

    def base64_decode_text(self, text: str) -> str:
        return base64_tools.decode_text(text)

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
        self._emit(progress, 0.02, "preparing", input_path.name)
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
                self._emit(progress, 0.05 + 0.9 * (processed / max(original_size, 1)), "encoding", input_path.name)
            if remainder:
                target.write(base64_tools.encode_bytes(remainder))
        self._emit(progress, 1.0, "done", output_path.name)
        return FileProcessResult(input_path, output_path, original_size, file_size(output_path), "base64")

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
        output_path = decrypted_output_path(input_path, out_dir, overwrite=self.settings.overwrite_outputs)
        original_size = file_size(input_path)
        processed = 0
        self._emit(progress, 0.02, "preparing", input_path.name)
        with input_path.open("rb") as source, atomic_binary_writer(output_path, overwrite=self.settings.overwrite_outputs) as target:
            buffer = b""
            while True:
                self._check_cancel(cancel_token)
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                processed += len(chunk)
                buffer += chunk.replace(b"\r", b"").replace(b"\n", b"")
                usable = (len(buffer) // 4) * 4
                if usable > 4:
                    target.write(base64_tools.decode_bytes(buffer[: usable - 4]))
                    buffer = buffer[usable - 4 :]
                self._emit(progress, 0.05 + 0.9 * (processed / max(original_size, 1)), "decoding", input_path.name)
            if buffer:
                target.write(base64_tools.decode_bytes(buffer))
        self._emit(progress, 1.0, "done", output_path.name)
        return FileProcessResult(input_path, output_path, original_size, file_size(output_path), "base64")

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

    def _emit(self, progress: ProgressCallback | None, percent: float, stage: str, detail: str = "") -> None:
        if progress:
            progress(ProgressEvent(max(0.0, min(1.0, percent)), stage, detail))

    def _check_cancel(self, cancel_token: CancelToken | None) -> None:
        if cancel_token and cancel_token.cancelled:
            raise OperationCancelled("Operation was cancelled.", code="operation.cancelled")
