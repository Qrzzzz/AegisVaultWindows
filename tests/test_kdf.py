from __future__ import annotations

import base64

import pytest

from aegisvault.core.exceptions import ProtocolError
from aegisvault.core.kdf import SCRYPT_N_MAX, ScryptParams, derive_key, params_from_header, params_to_header


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

