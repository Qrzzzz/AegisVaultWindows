"""AegisVault v1 envelope format helpers."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import struct
from datetime import UTC, datetime
from typing import Any, BinaryIO

from aegisvault.core.exceptions import ProtocolError

TEXT_PREFIX = "AGV1."
TEXT_MAGIC = b"AGVTEXT\x01"
FILE_MAGIC = b"AGVFILE\x01"
PROTOCOL_VERSION = 1
HEADER_MAX_SIZE = 64 * 1024
MIN_CHUNK_SIZE = 64 * 1024
MAX_CHUNK_SIZE = 16 * 1024 * 1024
MAX_CIPHERTEXT_CHUNK_SIZE = MAX_CHUNK_SIZE + 16
FLAG_LAST_CHUNK = 0x01
CHUNK_RECORD = struct.Struct(">BI")


def now_utc() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(data: dict[str, Any]) -> bytes:
    """Encode protocol JSON in a stable representation."""

    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_header(raw: bytes) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid protocol header.", code="crypto.invalid_header") from exc
    if not isinstance(data, dict):
        raise ProtocolError("Protocol header must be a JSON object.", code="crypto.invalid_header")
    return data


def header_digest(header_bytes: bytes) -> bytes:
    return hashlib.sha256(header_bytes).digest()


def encode_token(package: bytes) -> str:
    encoded = base64.urlsafe_b64encode(package).decode("ascii").rstrip("=")
    return TEXT_PREFIX + encoded


def decode_token(token: str) -> bytes:
    if not token.startswith(TEXT_PREFIX):
        raise ProtocolError("Unsupported text token.", code="crypto.unsupported_format")
    payload = token[len(TEXT_PREFIX) :].strip()
    padding = "=" * (-len(payload) % 4)
    try:
        return base64.urlsafe_b64decode(payload + padding)
    except (ValueError, binascii.Error) as exc:
        raise ProtocolError("Invalid text token encoding.", code="crypto.invalid_encoding") from exc


def pack_envelope(magic: bytes, header: dict[str, Any], payload: bytes) -> bytes:
    header_bytes = canonical_json(header)
    if len(header_bytes) > HEADER_MAX_SIZE:
        raise ProtocolError("Protocol header is too large.", code="crypto.header_too_large")
    return magic + struct.pack(">I", len(header_bytes)) + header_bytes + payload


def unpack_envelope(magic: bytes, package: bytes) -> tuple[dict[str, Any], bytes, bytes]:
    if not package.startswith(magic):
        raise ProtocolError("Unsupported encrypted data format.", code="crypto.unsupported_format")
    offset = len(magic)
    if len(package) < offset + 4:
        raise ProtocolError("Encrypted data is truncated.", code="crypto.truncated")
    header_len = struct.unpack(">I", package[offset : offset + 4])[0]
    offset += 4
    if header_len <= 0 or header_len > HEADER_MAX_SIZE:
        raise ProtocolError("Invalid protocol header length.", code="crypto.invalid_header")
    end = offset + header_len
    if len(package) < end:
        raise ProtocolError("Encrypted data is truncated.", code="crypto.truncated")
    header_bytes = package[offset:end]
    return parse_header(header_bytes), header_bytes, package[end:]


def read_exact(stream: BinaryIO, size: int) -> bytes:
    if size < 0 or size > MAX_CIPHERTEXT_CHUNK_SIZE:
        raise ProtocolError("Chunk record exceeds safety limits.", code="crypto.invalid_chunk")
    data = stream.read(size)
    if len(data) != size:
        raise ProtocolError("Encrypted data is truncated.", code="crypto.truncated")
    return data


def write_file_header(stream: BinaryIO, header: dict[str, Any]) -> bytes:
    header_bytes = canonical_json(header)
    if len(header_bytes) > HEADER_MAX_SIZE:
        raise ProtocolError("Protocol header is too large.", code="crypto.header_too_large")
    stream.write(FILE_MAGIC)
    stream.write(struct.pack(">I", len(header_bytes)))
    stream.write(header_bytes)
    return header_bytes


def read_file_header(stream: BinaryIO) -> tuple[dict[str, Any], bytes]:
    magic = read_exact(stream, len(FILE_MAGIC))
    if magic != FILE_MAGIC:
        raise ProtocolError("Unsupported file format.", code="crypto.unsupported_format")
    header_len = struct.unpack(">I", read_exact(stream, 4))[0]
    if header_len <= 0 or header_len > HEADER_MAX_SIZE:
        raise ProtocolError("Invalid protocol header length.", code="crypto.invalid_header")
    header_bytes = read_exact(stream, header_len)
    return parse_header(header_bytes), header_bytes


def validate_common_header(header: dict[str, Any], *, kind: str) -> None:
    if header.get("format") != f"aegisvault.{kind}":
        raise ProtocolError("Encrypted data type does not match this operation.", code="crypto.format_mismatch")
    if header.get("version") != PROTOCOL_VERSION:
        raise ProtocolError("Unsupported protocol version.", code="crypto.unsupported_version")
    if header.get("algorithm") != "AES-256-GCM":
        raise ProtocolError("Unsupported encryption algorithm.", code="crypto.unsupported_algorithm")


def validate_chunk_size(value: Any) -> int:
    try:
        chunk_size = int(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Invalid chunk size.", code="crypto.invalid_chunk_size") from exc
    if not (MIN_CHUNK_SIZE <= chunk_size <= MAX_CHUNK_SIZE):
        raise ProtocolError("Chunk size is outside safety limits.", code="crypto.invalid_chunk_size")
    return chunk_size


def validate_chunk_record(flags: int, ciphertext_len: int, chunk_size: int) -> None:
    if flags not in (0, FLAG_LAST_CHUNK):
        raise ProtocolError("Invalid chunk flags.", code="crypto.invalid_chunk")
    if ciphertext_len < 16:
        raise ProtocolError("Invalid chunk length.", code="crypto.invalid_chunk")
    if ciphertext_len > chunk_size + 16 or ciphertext_len > MAX_CIPHERTEXT_CHUNK_SIZE:
        raise ProtocolError("Chunk length exceeds safety limits.", code="crypto.invalid_chunk")


def chunk_aad(digest: bytes, index: int, flags: int) -> bytes:
    return b"AGV1-FILE-CHUNK|" + digest + struct.pack(">QB", index, flags)


def chunk_nonce(prefix: bytes, index: int) -> bytes:
    if len(prefix) != 8:
        raise ProtocolError("Invalid nonce prefix.", code="crypto.invalid_nonce")
    if index > 0xFFFFFFFF:
        raise ProtocolError("File has too many chunks.", code="crypto.too_many_chunks")
    return prefix + struct.pack(">I", index)
