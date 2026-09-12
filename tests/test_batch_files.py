from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import pytest

from aegisvault.backend.server import BackendServer
from aegisvault.core.exceptions import ValidationError
from aegisvault.core.models import CancelToken, ProgressEvent
from aegisvault.services.batch_service import MAX_BATCH_FILES, process_files
from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from test_backend_protocol import Client


@pytest.mark.parametrize("forward,reverse", [("file.encrypt", "file.decrypt"), ("base64.encode_file", "base64.decode_file")])
def test_batch_roundtrip_independent_outputs_and_no_overwrite(tmp_path: Path, forward: str, reverse: str) -> None:
    source, output, restored = [tmp_path / name for name in ("source", "output", "restored")]
    for folder in (source, output, restored):
        folder.mkdir()
    paths = [source / "笔记.txt", source / "empty", source / "binary.dat"]
    payloads = ["内容\r\n🔐".encode(), b"", bytes(range(256)) * 4100]
    for path, payload in zip(paths, payloads, strict=True):
        path.write_bytes(payload)
    settings = AppSettings(overwrite_outputs=True)
    first = process_files(settings, forward, list(map(str, paths)), output_dir=output, password="batch-password")
    second = process_files(settings, forward, list(map(str, paths)), output_dir=output, password="batch-password")
    assert all(item.status == "completed" for item in first.items + second.items)
    wrappers = [item.result.output_path for item in first.items if item.result]
    assert set(wrappers).isdisjoint(item.result.output_path for item in second.items if item.result)
    restored_batch = process_files(settings, reverse, list(map(str, wrappers)), output_dir=restored, password="batch-password")
    assert [item.result.output_path.read_bytes() for item in restored_batch.items if item.result] == payloads
    assert [path.read_bytes() for path in paths] == payloads
    assert not list(tmp_path.rglob(".*.tmp"))


def test_batch_failure_does_not_skip_later_files(tmp_path: Path) -> None:
    bad, missing, good = [tmp_path / name for name in ("bad.b64", "missing.b64", "good.b64")]
    bad.write_bytes(b"not valid @@")
    good.write_bytes(base64.b64encode(b"valid after errors"))
    result = process_files(AppSettings(), "base64.decode_file", [str(bad), str(missing), str(good)])
    assert [item.status for item in result.items] == ["failed", "failed", "completed"]
    assert result.items[0].code == "base64.invalid_data"
    assert result.items[1].code == "file.not_found"
    assert result.items[2].result and result.items[2].result.output_path.read_bytes() == b"valid after errors"
    assert not (tmp_path / "bad").exists()
    assert not list(tmp_path.rglob(".*.tmp"))


def test_batch_same_name_inputs_and_later_input_are_preserved(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    a, b, c = first / "report.txt", second / "report.txt", tmp_path / "report.txt.b64"
    for index, path in enumerate((a, b, c)):
        path.write_bytes(str(index).encode())
    result = process_files(AppSettings(overwrite_outputs=True), "base64.encode_file", list(map(str, (a, b, c))), output_dir=tmp_path)
    assert [item.status for item in result.items] == ["completed"] * 3
    outputs = [item.result.output_path for item in result.items if item.result]
    assert len(set(outputs)) == 3
    assert outputs[0].name == "report (1).txt.b64"
    assert outputs[1].name == "report (2).txt.b64"
    assert c.read_bytes() == b"2"


@pytest.mark.parametrize("invalid", [None, {}, [], [12], [""], ["a\0b"], ["\ud800"], ["x" * 32768], ["x"] * (MAX_BATCH_FILES + 1)])
def test_batch_rejects_bad_shape_before_any_output(tmp_path: Path, invalid: object) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"must not process")
    server = BackendServer(BytesIO(), BytesIO(), SettingsStore(tmp_path / "settings.json"))
    paths = [str(source), *invalid] if isinstance(invalid, list) and invalid else invalid
    with pytest.raises(ValidationError):
        server.dispatch("file.batch", {"operation": "base64.encode_file", "input_paths": paths}, lambda _: None)
    assert not (tmp_path / "source.txt.b64").exists()


def test_batch_rejects_duplicate_normalized_input(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"duplicate")
    with pytest.raises(ValidationError) as error:
        process_files(AppSettings(), "base64.encode_file", [str(source), str(source.parent / "." / source.name)])
    assert error.value.code == "validation.duplicate_file"
    assert not (tmp_path / "source.b64").exists()


def test_batch_cancel_between_files_retains_committed_results(tmp_path: Path) -> None:
    paths = [tmp_path / str(i) for i in range(3)]
    for path in paths:
        path.write_bytes(b"keep if complete")
    token = CancelToken()

    def progress(event: ProgressEvent) -> None:
        if event.stage == "batch.item_finished":
            token.cancel()

    result = process_files(AppSettings(), "base64.encode_file", list(map(str, paths)), progress=progress, cancel_token=token)
    assert result.cancelled
    assert [item.status for item in result.items] == ["completed", "pending", "pending"]
    assert result.items[0].result and result.items[0].result.output_path.exists()
    assert len(list(tmp_path.glob("*.b64"))) == 1


@pytest.mark.parametrize("operation", ["file.encrypt", "base64.encode_file"])
def test_batch_cancel_active_file_cleans_temporary_output(tmp_path: Path, operation: str) -> None:
    source = tmp_path / "large"
    source.write_bytes(b"x" * 3_000_000)
    token = CancelToken()

    def progress(event: ProgressEvent) -> None:
        if event.processed_bytes:
            token.cancel()

    result = process_files(AppSettings(), operation, [str(source)], password="test-password", progress=progress, cancel_token=token)
    assert result.cancelled
    assert result.items[0].status == "cancelled"
    assert list(tmp_path.iterdir()) == [source]


def test_real_backend_batch_protocol_progress_and_partial_failure(tmp_path: Path) -> None:
    good, missing = tmp_path / "real.txt", tmp_path / "missing.txt"
    good.write_bytes(b"real process")
    client = Client(tmp_path)
    try:
        client.send("file.batch", {"operation": "base64.encode_file", "input_paths": [str(missing), str(good)]})
        terminal, progress = client.terminal()
        assert terminal["type"] == "result"
        items = terminal["result"]["items"]
        assert [item["status"] for item in items] == ["failed", "completed"]
        assert Path(items[1]["result"]["output_path"]).read_bytes() == base64.b64encode(good.read_bytes())
        percentages = [event["percent"] for event in progress]
        assert percentages == sorted(percentages)
        assert percentages[-1] == 1
    finally:
        client.close()


def test_batch_metadata_budget_rejects_before_processing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import aegisvault.services.batch_service as batch

    source = tmp_path / "source"
    source.write_bytes(b"must not write")
    monkeypatch.setattr(batch, "MAX_BATCH_PATH_BYTES", 10)
    with pytest.raises(ValidationError) as error:
        batch.process_files(AppSettings(), "base64.encode_file", [str(source)])
    assert error.value.code == "resource.limit_exceeded"
    assert list(tmp_path.iterdir()) == [source]


def test_batch_pre_cancelled_request_never_starts_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.write_bytes(b"must not write")
    token = CancelToken()
    token.cancel()
    result = process_files(AppSettings(), "base64.encode_file", [str(source)], cancel_token=token)
    assert result.cancelled and result.items[0].status == "pending"
    assert list(tmp_path.iterdir()) == [source]


def test_batch_wrong_password_failure_then_valid_decryption(tmp_path: Path) -> None:
    sources = [tmp_path / str(index) for index in range(2)]
    for source in sources:
        source.write_bytes(b"authenticate each independently")
    encrypted = [process_files(AppSettings(), "file.encrypt", [str(source)], password=password).items[0].result
                 for source, password in zip(sources, ["wrong-password", "batch-password"], strict=True)]
    result = process_files(AppSettings(), "file.decrypt", [str(item.output_path) for item in encrypted if item], password="batch-password")
    assert [item.status for item in result.items] == ["failed", "completed"]
    assert result.items[0].code == "crypto.authentication_failed"
    assert result.items[1].result and result.items[1].result.output_path.read_bytes() == sources[1].read_bytes()
    assert not list(tmp_path.rglob(".*.tmp"))
