"""Modern AegisVault encryption and decryption routines."""

from __future__ import annotations

import base64
import binascii
import os
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aegisvault.core.exceptions import (
    AuthenticationError,
    FileIOError,
    OperationCancelled,
    ProtocolError,
    ResourceLimitError,
    ValidationError,
)
from aegisvault.core.file_io import atomic_binary_writer, ensure_distinct_paths, ensure_input_unchanged, file_size
from aegisvault.core.kdf import ScryptParams, derive_key, make_scrypt_params, params_from_header, params_to_header
from aegisvault.core.models import (
    CancelToken,
    FileProcessResult,
    ProgressCallback,
    ProgressEvent,
    TextDecryptResult,
    TextEncryptResult,
)
from aegisvault.core.protocol import (
    CHUNK_RECORD,
    FILE_MAGIC,
    FLAG_LAST_CHUNK,
    TEXT_MAGIC,
    chunk_aad,
    chunk_nonce,
    decode_token,
    encode_token,
    header_digest,
    now_utc,
    pack_envelope,
    read_exact,
    read_file_header,
    unpack_envelope,
    validate_chunk_record,
    validate_chunk_size,
    validate_file_header,
    validate_text_header,
    write_file_header,
)
from aegisvault.resource_limits import TEXT_LIMITS

DEFAULT_CHUNK_SIZE = 1024 * 1024


def _emit(
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


def _check_cancel(cancel_token: CancelToken | None) -> None:
    if cancel_token and cancel_token.cancelled:
        raise OperationCancelled("Operation was cancelled.", code="operation.cancelled")


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(value: Any, *, field: str) -> bytes:
    if not isinstance(value, str):
        raise ProtocolError(f"Invalid base64 field: {field}", code="crypto.invalid_header")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ProtocolError(f"Invalid base64 field: {field}", code="crypto.invalid_header") from exc


def encrypt_text(plaintext: str, password: str, *, kdf_params: ScryptParams | None = None) -> TextEncryptResult:
    """Encrypt UTF-8 text into an ``AGV1.`` token."""

    _require_password(password)
    params = kdf_params or make_scrypt_params()
    nonce = os.urandom(12)
    header: dict[str, Any] = {
        "format": "aegisvault.text",
        "version": 1,
        "algorithm": "AES-256-GCM",
        "kdf": params_to_header(params),
        "nonce": _b64(nonce),
        "created_at": now_utc(),
    }
    header_package = pack_envelope(TEXT_MAGIC, header, b"")
    _, header_bytes, _ = unpack_envelope(TEXT_MAGIC, header_package)
    aesgcm = AESGCM(derive_key(password, params))
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), header_bytes)
    return TextEncryptResult(encode_token(pack_envelope(TEXT_MAGIC, header, ciphertext)), "aegisvault-v1")


def decrypt_text(token: str, password: str) -> TextDecryptResult:
    """Decrypt a modern ``AGV1.`` text token."""

    package = decode_token(token.strip())
    _require_password(password)
    header, header_bytes, ciphertext = unpack_envelope(TEXT_MAGIC, package)
    if len(ciphertext) >= 16 and len(ciphertext) - 16 > TEXT_LIMITS.max_plaintext_utf8_bytes:
        raise ResourceLimitError("AGV1 plaintext exceeds the text-workflow budget.")
    validate_text_header(header)
    nonce = _unb64(header.get("nonce"), field="nonce")
    if len(nonce) != 12:
        raise ProtocolError("Invalid nonce length.", code="crypto.invalid_nonce")
    params = params_from_header(_expect_dict(header.get("kdf"), "kdf"))
    aesgcm = AESGCM(derive_key(password, params))
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, header_bytes)
    except InvalidTag as exc:
        raise AuthenticationError("Authentication failed.", code="crypto.authentication_failed") from exc
    try:
        return TextDecryptResult(plaintext.decode("utf-8"), "aegisvault-v1")
    except UnicodeDecodeError as exc:
        raise ProtocolError("Decrypted data is not UTF-8 text.", code="crypto.invalid_plaintext") from exc


def encrypt_file(
    input_path: Path,
    output_path: Path,
    password: str,
    *,
    overwrite: bool = False,
    kdf_params: ScryptParams | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    progress: ProgressCallback | None = None,
    cancel_token: CancelToken | None = None,
) -> FileProcessResult:
    """Encrypt a file as an AegisVault v1 chunked container."""

    input_path = input_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    _require_password(password)
    ensure_distinct_paths(input_path, output_path)
    original_size = file_size(input_path)
    chunk_size = validate_chunk_size(chunk_size)
    params = kdf_params or make_scrypt_params()
    nonce_prefix = os.urandom(8)
    header: dict[str, Any] = {
        "format": "aegisvault.file",
        "version": 1,
        "algorithm": "AES-256-GCM",
        "mode": "chunked",
        "kdf": params_to_header(params),
        "chunk_size": chunk_size,
        "nonce_prefix": _b64(nonce_prefix),
        "metadata": {
            "original_suffix": input_path.suffix,
            "original_size": original_size,
        },
        "created_at": now_utc(),
    }
    aesgcm = AESGCM(derive_key(password, params))
    bytes_read = 0

    _emit(progress, 0.02, "preparing", input_path.name, processed_bytes=0, total_bytes=original_size)
    with input_path.open("rb") as source, atomic_binary_writer(output_path, overwrite=overwrite) as target:
        source_stat = os.fstat(source.fileno())
        if source_stat.st_size != original_size:
            raise FileIOError("Input file changed before encryption.", code="file.input_changed")
        header_bytes = write_file_header(target, header)
        digest = header_digest(header_bytes)
        index = 0

        chunk = source.read(chunk_size)
        if chunk == b"":
            _check_cancel(cancel_token)
            ciphertext = aesgcm.encrypt(chunk_nonce(nonce_prefix, index), b"", chunk_aad(digest, index, FLAG_LAST_CHUNK))
            target.write(CHUNK_RECORD.pack(FLAG_LAST_CHUNK, len(ciphertext)))
            target.write(ciphertext)
            _emit(progress, 0.95, "encrypting", input_path.name, processed_bytes=0, total_bytes=original_size)
        else:
            while True:
                _check_cancel(cancel_token)
                next_chunk = source.read(chunk_size)
                flags = FLAG_LAST_CHUNK if next_chunk == b"" else 0
                ciphertext = aesgcm.encrypt(chunk_nonce(nonce_prefix, index), chunk, chunk_aad(digest, index, flags))
                target.write(CHUNK_RECORD.pack(flags, len(ciphertext)))
                target.write(ciphertext)
                bytes_read += len(chunk)
                _emit(
                    progress,
                    0.05 + 0.9 * (bytes_read / max(original_size, 1)),
                    "encrypting",
                    input_path.name,
                    processed_bytes=bytes_read,
                    total_bytes=original_size,
                )
                if flags & FLAG_LAST_CHUNK:
                    break
                chunk = next_chunk
                index += 1
        ensure_input_unchanged(source, source_stat, bytes_read)
        _check_cancel(cancel_token)
        _emit(progress, 1.0, "done", output_path.name, processed_bytes=original_size, total_bytes=original_size)
        _check_cancel(cancel_token)
        output_size = target.tell()
    return FileProcessResult(input_path, output_path, original_size, output_size, "aegisvault-v1")


def decrypt_file(
    input_path: Path,
    output_path: Path,
    password: str,
    *,
    overwrite: bool = False,
    progress: ProgressCallback | None = None,
    cancel_token: CancelToken | None = None,
) -> FileProcessResult:
    """Decrypt a modern AegisVault file container."""

    input_path = input_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    ensure_distinct_paths(input_path, output_path)
    encrypted_size = file_size(input_path)
    _emit(progress, 0.02, "preparing", input_path.name, processed_bytes=0, total_bytes=encrypted_size)

    with input_path.open("rb") as source:
        header, header_bytes = read_file_header(source)
        _require_password(password)
        chunk_size = validate_file_header(header)
        params = params_from_header(_expect_dict(header.get("kdf"), "kdf"))
        nonce_prefix = _unb64(header.get("nonce_prefix"), field="nonce_prefix")
        if len(nonce_prefix) != 8:
            raise ProtocolError("Invalid nonce prefix.", code="crypto.invalid_nonce")
        aesgcm = AESGCM(derive_key(password, params))
        digest = header_digest(header_bytes)

        with atomic_binary_writer(output_path, overwrite=overwrite) as target:
            index = 0
            found_last = False
            plaintext_size = 0
            while True:
                _check_cancel(cancel_token)
                record = source.read(CHUNK_RECORD.size)
                if record == b"":
                    break
                if len(record) != CHUNK_RECORD.size:
                    raise ProtocolError("Truncated chunk record.", code="crypto.truncated")
                flags, ciphertext_len = CHUNK_RECORD.unpack(record)
                validate_chunk_record(flags, ciphertext_len, chunk_size)
                ciphertext = read_exact(source, ciphertext_len)
                try:
                    plaintext = aesgcm.decrypt(chunk_nonce(nonce_prefix, index), ciphertext, chunk_aad(digest, index, flags))
                except InvalidTag as exc:
                    raise AuthenticationError("Authentication failed.", code="crypto.authentication_failed") from exc
                target.write(plaintext)
                plaintext_size += len(plaintext)
                _emit(
                    progress,
                    0.05 + 0.9 * (source.tell() / max(encrypted_size, 1)),
                    "decrypting",
                    input_path.name,
                    processed_bytes=source.tell(),
                    total_bytes=encrypted_size,
                )
                if flags & FLAG_LAST_CHUNK:
                    found_last = True
                    trailing = source.read(1)
                    if trailing:
                        raise ProtocolError("Unexpected trailing data.", code="crypto.trailing_data")
                    break
                index += 1
            if not found_last:
                raise ProtocolError("Missing final chunk.", code="crypto.truncated")
            metadata = _expect_dict(header.get("metadata"), "metadata")
            if plaintext_size != metadata["original_size"]:
                raise ProtocolError("Decrypted file size does not match its header.", code="crypto.size_mismatch")
            _check_cancel(cancel_token)
            _emit(progress, 1.0, "done", output_path.name, processed_bytes=encrypted_size, total_bytes=encrypted_size)
            _check_cancel(cancel_token)
            output_size = target.tell()
    return FileProcessResult(input_path, output_path, encrypted_size, output_size, "aegisvault-v1")


def is_modern_file(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(FILE_MAGIC)) == FILE_MAGIC


def _expect_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError(f"Header field is not an object: {field}", code="crypto.invalid_header")
    return value


def _require_password(password: str) -> None:
    if not isinstance(password, str) or password == "":
        raise ValidationError("Password is required.", code="validation.password_required")
