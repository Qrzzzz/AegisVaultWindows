from __future__ import annotations

import base64
from pathlib import Path

import pytest

from aegisvault.core.base64_tools import Base64StreamDecoder
from aegisvault.core.exceptions import OperationCancelled, ValidationError
from aegisvault.core.models import CancelToken, ProgressEvent
from aegisvault.services.crypto_service import CryptoService
from aegisvault.settings.models import AppSettings


@pytest.mark.parametrize("block_size", range(1, 9))
def test_stream_decoder_handles_quartets_and_whitespace_split_at_every_small_boundary(block_size: int) -> None:
    plaintext = "跨块 🔐 / whitespace".encode()
    encoded = base64.b64encode(plaintext)
    wrapped = b" \r\n".join(encoded[index : index + 3] for index in range(0, len(encoded), 3))
    decoder = Base64StreamDecoder(strict=False, ignore_ascii_whitespace=True)
    decoded = b""

    for index in range(0, len(wrapped), block_size):
        decoded += decoder.feed(wrapped[index : index + block_size])
    decoded += decoder.finalize()

    assert decoded == plaintext


def test_stream_decoder_allows_only_whitespace_after_padding() -> None:
    decoder = Base64StreamDecoder(strict=False, ignore_ascii_whitespace=True)
    assert decoder.feed(b"YQ==") == b"a"
    assert decoder.feed(b"\r\n \t") == b""
    assert decoder.finalize() == b""


def test_stream_decoder_rejects_data_after_padding_in_later_block() -> None:
    decoder = Base64StreamDecoder(strict=False, ignore_ascii_whitespace=True)
    assert decoder.feed(b"YQ==") == b"a"
    with pytest.raises(ValidationError):
        decoder.feed(b"Yg==")


def test_base64_empty_file_round_trip_with_unicode_path(tmp_path: Path) -> None:
    source = tmp_path / "空 文件 🔐.bin"
    source.write_bytes(b"")
    service = CryptoService(AppSettings())

    encoded = service.base64_encode_file(source)
    restored = service.base64_decode_file(encoded.output_path)

    assert encoded.output_path.read_bytes() == b""
    assert restored.output_path.read_bytes() == b""


def test_malformed_base64_file_leaves_no_output_or_temporary_file(tmp_path: Path) -> None:
    source = tmp_path / "malformed.b64"
    source.write_bytes(b"YQ==not-allowed")

    with pytest.raises(ValidationError):
        CryptoService(AppSettings()).base64_decode_file(source)

    assert not (tmp_path / "malformed").exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_base64_final_progress_cancellation_leaves_no_output(tmp_path: Path) -> None:
    source = tmp_path / "payload.bin"
    source.write_bytes(b"payload")
    token = CancelToken()

    def cancel_when_done(event: ProgressEvent) -> None:
        if event.stage == "done":
            token.cancel()

    with pytest.raises(OperationCancelled):
        CryptoService(AppSettings()).base64_encode_file(source, progress=cancel_when_done, cancel_token=token)

    assert not (tmp_path / "payload.bin.b64").exists()
    assert not list(tmp_path.glob(".*.tmp"))
