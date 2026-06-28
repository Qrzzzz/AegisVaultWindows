from __future__ import annotations

from pathlib import Path

import pytest

from aegisvault.core.crypto import encrypt_file
from aegisvault.core.exceptions import OperationCancelled
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.models import CancelToken
from aegisvault.core.protocol import MIN_CHUNK_SIZE


def test_cancel_removes_temporary_output(tmp_path: Path) -> None:
    source = tmp_path / "large.bin"
    output = tmp_path / "large.bin.agv"
    source.write_bytes(b"x" * (MIN_CHUNK_SIZE * 3))
    token = CancelToken()

    def cancel_on_first_progress(*_args: object) -> None:
        token.cancel()

    with pytest.raises(OperationCancelled):
        encrypt_file(
            source,
            output,
            "passphrase",
            kdf_params=ScryptParams(salt=b"c" * 16, n=2**14),
            chunk_size=MIN_CHUNK_SIZE,
            progress=cancel_on_first_progress,
            cancel_token=token,
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))
