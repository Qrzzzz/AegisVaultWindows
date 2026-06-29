# AegisVault Protocol

This document describes the modern formats produced by AegisVault 1.0.0. Legacy formats are recovery-only and are documented in `docs/MIGRATION.md`.

## Text Token

Modern encrypted text is emitted as:

```text
AGV1.<base64url-envelope>
```

The decoded envelope contains:

1. `AGVTEXT\x01` magic bytes.
2. A 32-bit big-endian header length.
3. A canonical UTF-8 JSON header.
4. AES-GCM ciphertext and tag.

The JSON header is sorted and compact. It is authenticated as AES-GCM AAD.

Required header fields:

- `format`: `aegisvault.text`.
- `version`: `1`.
- `algorithm`: `AES-256-GCM`.
- `kdf`: scrypt parameters.
- `nonce`: Base64 encoded 12-byte text nonce.
- `created_at`: UTC timestamp.

## File Container

Modern encrypted files use the `.agv` suffix and start with:

1. `AGVFILE\x01` magic bytes.
2. A 32-bit big-endian header length.
3. A canonical UTF-8 JSON header.
4. Zero or more chunk records.

Required file header fields:

- `format`: `aegisvault.file`.
- `version`: `1`.
- `algorithm`: `AES-256-GCM`.
- `mode`: `chunked`.
- `kdf`: scrypt parameters.
- `chunk_size`: plaintext chunk size.
- `nonce_prefix`: Base64 encoded 8-byte nonce prefix.
- `metadata.original_suffix`: original file suffix.
- `metadata.original_size`: original input size.
- `created_at`: UTC timestamp.

The header size is limited to 64 KiB.

## KDF

Modern encryption uses scrypt. The current default is:

```text
N=32768, r=8, p=1, salt_len=16, key_len=32
```

Decryptors reject unsafe or malformed KDF parameters, including non-power-of-two `N`, excessive `N`, excessive `r` or `p`, too-short salt, and non-32-byte key lengths.

## Chunk Records

Each file chunk record is:

```text
1 byte flags | 4 byte ciphertext length | ciphertext
```

`0x01` marks the final chunk. Empty files are represented by one final encrypted empty chunk.

The chunk nonce is:

```text
8 byte nonce_prefix | 4 byte chunk_index
```

The chunk index is bounded to 32 bits. A file that would overflow the index is rejected.

## AAD

Each chunk authenticates:

```text
"AGV1-FILE-CHUNK|" | sha256(header_bytes) | chunk_index | flags
```

This detects header tampering, chunk tampering, missing final chunks, truncated chunk records, unexpected trailing data and invalid chunk lengths.

## Versioning

New incompatible formats must use a new magic/version combination. AegisVault 1.0.0 only writes version 1. Legacy formats are not written by modern workflows.
