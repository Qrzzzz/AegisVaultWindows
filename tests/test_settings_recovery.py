from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from aegisvault.settings.models import AppSettings
from aegisvault.settings.store import SettingsStore
from test_backend_protocol import Client


@pytest.mark.parametrize("config", ["long_integer", "bad_json", "valid"])
@pytest.mark.parametrize("operation", ["settings.get", "settings.update", "base64.encode_text"])
def test_bad_config_recovers_through_real_backend(tmp_path: Path, config: str, operation: str) -> None:
    path = tmp_path / "AegisVault" / "settings.json"
    path.parent.mkdir()
    original_limit = sys.get_int_max_str_digits()
    valid = AppSettings(language="en-US", theme="system", show_advanced_options=True)
    raw = {
        "long_integer": '{"language":' + "9" * 5000 + "}",
        "bad_json": "{broken",
        "valid": json.dumps(valid.to_dict()),
    }[config]
    path.write_text(raw, encoding="utf-8")
    args = {"settings.get": {}, "settings.update": {"theme": "dark"}, "base64.encode_text": {"text": "abc"}}
    client = Client(tmp_path)
    try:
        client.send(operation, args[operation])
        event, _ = client.terminal()
        assert event["type"] == "result", event
        if operation == "base64.encode_text":
            assert event["result"]["text"] == "YWJj"
        elif operation == "settings.get":
            assert event["result"] == (valid if config == "valid" else AppSettings()).to_dict()
        else:
            assert event["result"]["theme"] == "dark"

        # Recovery remains usable: a subsequent update really persists, then
        # both settings reads and ordinary business work in the same process.
        client.send("settings.update", {"theme": "dark", "show_advanced_options": True})
        assert client.receive()["result"]["show_advanced_options"] is True
        client.send("settings.get")
        restored = client.receive()["result"]
        assert restored["theme"] == "dark" and restored["show_advanced_options"] is True
        client.send("base64.encode_text", {"text": "abc"})
        assert client.receive()["result"]["text"] == "YWJj"
        client.send("base64.decode_text", {"text": "YWJj"})
        assert client.receive()["result"]["text"] == "abc"
    finally:
        client.close()
    assert json.loads(path.read_text("utf-8"))["theme"] == "dark"
    assert SettingsStore(path).load().show_advanced_options is True
    assert sys.get_int_max_str_digits() == original_limit


def test_model_errors_are_not_silently_treated_as_bad_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{}", encoding="utf-8")

    def broken_model(_data):
        raise ValueError("model programming error")

    monkeypatch.setattr(AppSettings, "from_dict", broken_model)
    with pytest.raises(ValueError, match="model programming error"):
        SettingsStore(path).load()
