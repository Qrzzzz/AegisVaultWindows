# Migration Notes

AegisVault 0.3.0-alpha is a rebuild of the legacy AES Encryption System v2.0 script. The legacy script is archived at `docs/legacy/legacy_aes_v2.py` for reference only.

## Legacy Format Detection

AegisVault can recover:

- Legacy text: `Base64(nonce + ciphertext)`.
- Legacy files: raw `nonce + ciphertext`.
- AK wrappers: `AK#key#ciphertext`, only when AK compatibility is enabled in Settings.

Modern text starts with `AGV1.`. Modern files start with the binary `AGVFILE` magic and usually use the `.agv` suffix.

## How To Migrate

1. Open the legacy ciphertext or file in AegisVault.
2. Enter the original password.
3. If the data uses `AK#key#ciphertext`, enable AK compatibility in Settings only for this migration.
4. Decrypt the data.
5. Re-encrypt the recovered plaintext/file with the modern AGV1 workflow.
6. Turn AK compatibility off again.

## Why Re-Encrypt

Legacy encryption used `sha256(password)` directly as the AES key and did not store KDF parameters. Modern AegisVault uses per-message salt, scrypt and a documented authenticated envelope.

## Why AK Is Dangerous

AK wrappers store the key next to the ciphertext. Anyone who receives the wrapper has everything needed to decrypt it. AK mode is not secure encryption; it only exists to avoid stranding old data.

## Large Legacy Files

Legacy file recovery is guarded by a size threshold. The old raw format cannot be safely authenticated in true streaming mode with the high-level legacy API, so very large files need a staged recovery plan.
