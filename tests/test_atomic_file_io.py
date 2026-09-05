from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

import aegisvault.core.file_io as file_io_module
from aegisvault.core.crypto import encrypt_file
from aegisvault.core.exceptions import FileIOError, OperationCancelled
from aegisvault.core.file_io import atomic_binary_writer
from aegisvault.core.kdf import ScryptParams
from aegisvault.core.models import CancelToken, ProgressEvent


def test_atomic_writer_refuses_racing_no_overwrite_creator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "result.bin"
    real_publish = file_io_module._publish_no_overwrite

    def racing_publish(source: str, target: Path) -> bool:
        target.write_bytes(b"competitor")
        return real_publish(source, target)

    monkeypatch.setattr(file_io_module, "_publish_no_overwrite", racing_publish)

    with pytest.raises(FileIOError) as caught, atomic_binary_writer(output, overwrite=False) as target:
        target.write(b"ours")

    assert caught.value.code == "file.output_exists"
    assert output.read_bytes() == b"competitor"
    assert not list(tmp_path.glob(".*.tmp"))


def test_atomic_writer_removes_temporary_file_on_body_exception(tmp_path: Path) -> None:
    output = tmp_path / "result.bin"

    with pytest.raises(RuntimeError, match="injected failure"), atomic_binary_writer(output) as target:
        target.write(b"partial")
        raise RuntimeError("injected failure")

    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_crypto_rejects_same_input_and_output_even_with_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "important.txt"
    original = b"must survive"
    source.write_bytes(original)

    with pytest.raises(FileIOError) as caught:
        encrypt_file(
            source,
            source,
            "passphrase",
            overwrite=True,
            kdf_params=ScryptParams(salt=b"s" * 16, n=2**14),
        )

    assert caught.value.code == "file.same_input_output"
    assert source.read_bytes() == original
    assert not list(tmp_path.glob(".*.tmp"))


def test_two_no_overwrite_writers_have_exactly_one_winner(tmp_path: Path) -> None:
    output = tmp_path / "shared.bin"
    ready = Barrier(2)

    def write(payload: bytes) -> str:
        try:
            with atomic_binary_writer(output, overwrite=False) as target:
                target.write(payload)
                ready.wait(timeout=5)
            return "published"
        except FileIOError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [b"first", b"second"]))

    assert sorted(results) == ["file.output_exists", "published"]
    assert output.read_bytes() in {b"first", b"second"}
    assert not list(tmp_path.glob(".*.tmp"))


def test_progress_exception_before_publish_leaves_no_output(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    output = tmp_path / "source.bin.agv"
    source.write_bytes(b"payload")

    def fail_when_done(event: ProgressEvent) -> None:
        if event.stage == "done":
            raise RuntimeError("progress observer failed")

    with pytest.raises(RuntimeError, match="progress observer failed"):
        encrypt_file(
            source,
            output,
            "passphrase",
            kdf_params=ScryptParams(salt=b"p" * 16, n=2**14),
            progress=fail_when_done,
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_cancellation_on_final_progress_still_prevents_publish(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    output = tmp_path / "source.bin.agv"
    source.write_bytes(b"payload")
    token = CancelToken()

    def cancel_when_done(event: ProgressEvent) -> None:
        if event.stage == "done":
            token.cancel()

    with pytest.raises(OperationCancelled):
        encrypt_file(
            source,
            output,
            "passphrase",
            kdf_params=ScryptParams(salt=b"c" * 16, n=2**14),
            progress=cancel_when_done,
            cancel_token=token,
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_input_change_before_streaming_prevents_encrypted_output(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    output = tmp_path / "source.bin.agv"
    source.write_bytes(b"original")

    def mutate_when_prepared(event: ProgressEvent) -> None:
        if event.stage == "preparing":
            source.write_bytes(b"changed and longer")

    with pytest.raises(FileIOError) as caught:
        encrypt_file(
            source,
            output,
            "passphrase",
            kdf_params=ScryptParams(salt=b"m" * 16, n=2**14),
            progress=mutate_when_prepared,
        )

    assert caught.value.code == "file.input_changed"
    assert not output.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_fixed_temporary_name_allows_legal_boundary_target(tmp_path: Path) -> None:
    output = tmp_path / ("a" * 251 + ".bin")
    output.write_bytes(b"writable-final-name")
    output.unlink()

    with atomic_binary_writer(output) as target:
        target.write(b"payload")

    assert output.read_bytes() == b"payload"
    assert not list(tmp_path.glob(".aegisvault-*.tmp"))


def test_temporary_name_is_bounded_and_does_not_disclose_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "sensitive-customer-report.txt"
    observed: list[str] = []
    real_publish = file_io_module._publish_no_overwrite

    def inspect_publish(source: str, target: Path) -> bool:
        observed.append(Path(source).name)
        return real_publish(source, target)

    monkeypatch.setattr(file_io_module, "_publish_no_overwrite", inspect_publish)
    with atomic_binary_writer(output) as target:
        target.write(b"payload")

    assert len(observed) == 1
    assert len(observed[0]) == 40
    assert observed[0].startswith(".aegisvault-") and observed[0].endswith(".tmp")
    assert "sensitive" not in observed[0]


def test_secure_temporary_name_collision_retries_exclusive_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = "11" * file_io_module.TEMP_RANDOM_BYTES
    second = "22" * file_io_module.TEMP_RANDOM_BYTES
    occupied = tmp_path / f"{file_io_module.TEMP_NAME_PREFIX}{first}{file_io_module.TEMP_NAME_SUFFIX}"
    occupied.write_bytes(b"competitor")
    names = iter([first, second])
    monkeypatch.setattr(file_io_module.secrets, "token_hex", lambda _size: next(names))

    output = tmp_path / "result.bin"
    with atomic_binary_writer(output) as target:
        target.write(b"ours")

    assert output.read_bytes() == b"ours"
    assert occupied.read_bytes() == b"competitor"
    assert not (tmp_path / f"{file_io_module.TEMP_NAME_PREFIX}{second}{file_io_module.TEMP_NAME_SUFFIX}").exists()


def test_illegal_final_component_fails_and_cleans_bounded_temporary(tmp_path: Path) -> None:
    output = tmp_path / ("a" * 252 + ".bin")

    with pytest.raises(FileIOError) as caught, atomic_binary_writer(output) as target:
        target.write(b"payload")

    assert caught.value.code == "file.write_failed"
    assert not output.exists()
    assert not list(tmp_path.glob(".aegisvault-*.tmp"))
