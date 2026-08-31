from __future__ import annotations

import base64

import pytest

import aegisvault.core.kdf as kdf_module
from aegisvault.core.exceptions import ProtocolError, ResourceLimitError
from aegisvault.core.kdf import (
    SCRYPT_N_MAX,
    ScryptParams,
    derive_key,
    params_from_header,
    params_to_header,
    validate_scrypt_params,
)


def test_scrypt_derivation_is_stable_for_same_parameters() -> None:
    params = ScryptParams(salt=b"0" * 16, n=2**14)
    assert derive_key("correct horse battery staple", params) == derive_key("correct horse battery staple", params)
    assert derive_key("correct horse battery staple", params) != derive_key("different password", params)


def test_kdf_parameters_round_trip_through_header() -> None:
    params = ScryptParams(salt=b"1" * 16, n=2**14, r=8, p=1, length=32)
    assert params_from_header(params_to_header(params)) == params


def test_malicious_kdf_parameters_are_rejected() -> None:
    header = {
        "type": "scrypt",
        "salt": base64.b64encode(b"s" * 16).decode("ascii"),
        "n": SCRYPT_N_MAX * 2,
        "r": 8,
        "p": 1,
        "length": 32,
    }
    with pytest.raises(ProtocolError):
        params_from_header(header)


def test_scrypt_n_must_be_power_of_two() -> None:
    with pytest.raises(ProtocolError):
        derive_key("password", ScryptParams(salt=b"s" * 16, n=2**14 + 1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("n", float(2**14)),
        ("n", str(2**14)),
        ("r", True),
        ("p", "1"),
        ("length", 32.0),
    ],
)
def test_kdf_header_rejects_coercible_non_integer_types(field: str, value: object) -> None:
    header: dict[str, object] = {
        "type": "scrypt",
        "salt": base64.b64encode(b"s" * 16).decode("ascii"),
        "n": 2**14,
        "r": 8,
        "p": 1,
        "length": 32,
    }
    header[field] = value
    with pytest.raises(ProtocolError):
        params_from_header(header)


def test_combined_scrypt_memory_budget_is_enforced() -> None:
    individually_valid_but_unsafe = ScryptParams(salt=b"s" * 16, n=2**20, r=16, p=1)
    with pytest.raises(ResourceLimitError):
        validate_scrypt_params(individually_valid_but_unsafe)


def test_combined_scrypt_work_budget_is_enforced_before_backend_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_backend_call(**_kwargs: object) -> object:
        raise AssertionError("scrypt backend must not be constructed for over-budget parameters")

    monkeypatch.setattr(kdf_module, "Scrypt", unexpected_backend_call)
    individually_valid_but_unsafe = ScryptParams(salt=b"s" * 16, n=2**20, r=1, p=8)
    with pytest.raises(ResourceLimitError):
        derive_key("password", individually_valid_but_unsafe)
