"""Password based key derivation.

The legacy application used ``sha256(password)`` directly as an AES key. This
module intentionally replaces that with scrypt, a memory-hard KDF available in
the widely used ``cryptography`` package and suitable for offline password
guessing resistance on desktop machines.
"""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from aegisvault.core.exceptions import ProtocolError, ValidationError

KDF_TYPE_SCRYPT = "scrypt"
SCRYPT_N_MIN = 2**14
SCRYPT_N_MAX = 2**20
SCRYPT_R_MIN = 1
SCRYPT_R_MAX = 16
SCRYPT_P_MIN = 1
SCRYPT_P_MAX = 8
SCRYPT_SALT_MIN = 16
SCRYPT_SALT_MAX = 64
SCRYPT_KEY_LENGTH = 32


@dataclass(frozen=True)
class ScryptParams:
    """Serializable scrypt parameters."""

    salt: bytes
    n: int = 2**15
    r: int = 8
    p: int = 1
    length: int = SCRYPT_KEY_LENGTH


def make_scrypt_params(*, n: int = 2**15, r: int = 8, p: int = 1, length: int = 32) -> ScryptParams:
    """Create fresh scrypt parameters with a random salt."""

    params = ScryptParams(salt=os.urandom(16), n=n, r=r, p=p, length=length)
    validate_scrypt_params(params)
    return params


def derive_key(password: str, params: ScryptParams) -> bytes:
    """Derive an AES key from a user password."""

    if not password:
        raise ValidationError("Password is required.", code="validation.password_required")
    validate_scrypt_params(params)
    kdf = Scrypt(salt=params.salt, length=params.length, n=params.n, r=params.r, p=params.p)
    return kdf.derive(password.encode("utf-8"))


def validate_scrypt_params(params: ScryptParams) -> None:
    """Validate KDF parameters before deriving keys or serializing headers."""

    if params.length != SCRYPT_KEY_LENGTH:
        raise ProtocolError("AES-256 requires a 32-byte key.", code="crypto.invalid_kdf")
    if not (SCRYPT_SALT_MIN <= len(params.salt) <= SCRYPT_SALT_MAX):
        raise ProtocolError("Invalid salt length.", code="crypto.invalid_kdf")
    if not (SCRYPT_N_MIN <= params.n <= SCRYPT_N_MAX) or params.n & (params.n - 1) != 0:
        raise ProtocolError("Invalid scrypt N parameter.", code="crypto.invalid_kdf")
    if not (SCRYPT_R_MIN <= params.r <= SCRYPT_R_MAX):
        raise ProtocolError("Invalid scrypt r parameter.", code="crypto.invalid_kdf")
    if not (SCRYPT_P_MIN <= params.p <= SCRYPT_P_MAX):
        raise ProtocolError("Invalid scrypt p parameter.", code="crypto.invalid_kdf")


def params_to_header(params: ScryptParams) -> dict[str, Any]:
    """Convert KDF parameters to a JSON-serializable protocol mapping."""

    validate_scrypt_params(params)
    return {
        "type": KDF_TYPE_SCRYPT,
        "salt": base64.b64encode(params.salt).decode("ascii"),
        "n": params.n,
        "r": params.r,
        "p": params.p,
        "length": params.length,
    }


def params_from_header(data: dict[str, Any]) -> ScryptParams:
    """Parse and validate KDF parameters from a protocol header."""

    if data.get("type") != KDF_TYPE_SCRYPT:
        raise ProtocolError("Unsupported KDF.", code="crypto.unsupported_kdf")
    try:
        salt = base64.b64decode(str(data["salt"]), validate=True)
        n = int(data["n"])
        r = int(data["r"])
        p = int(data["p"])
        length = int(data["length"])
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        raise ProtocolError("Invalid KDF parameters.", code="crypto.invalid_kdf") from exc
    params = ScryptParams(salt=salt, n=n, r=r, p=p, length=length)
    validate_scrypt_params(params)
    return params
