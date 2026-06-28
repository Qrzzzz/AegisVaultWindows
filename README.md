# AegisVault

AegisVault is a local Windows desktop tool for text encryption, file encryption, Base64 encoding and explicit legacy encrypted-data recovery. The `0.4.0-alpha` line focuses on hardening, clearer workflows and a restrained Windows desktop UI.

The legacy reference script is archived at `docs/legacy/legacy_aes_v2.py`; it is excluded from linting and type checking.

## Verified Scope

- Text encryption and decryption with the `AGV1.` token format.
- File encryption and decryption with the `.agv` chunked AES-GCM container.
- Base64 text and file encode/decode as encoding workflows, not encryption.
- Inline error display for normal page-level failures.
- Settings for theme, language, output directory, overwrite behavior, recent files, legacy recovery visibility and AK compatibility.
- Legacy text/file recovery and AK wrapper parsing as compatibility-only paths. AK parsing is off by default.
- Windows packaging through PyInstaller via `scripts/build_windows.ps1`.

## Security Design

New encryption uses AES-256-GCM and scrypt with per-encryption random salt. Text tokens authenticate their protocol header as AAD. File encryption is chunked, and each chunk authenticates the header hash, chunk index and final-chunk flag.

The core and service layers reject empty passwords for normal encryption and decryption paths. Header sizes, chunk sizes, ciphertext record lengths and legacy whole-file recovery are bounded. File writes use temporary files and atomic replace on success; cancellation and failures must not leave a fake successful output.

## Boundaries

AegisVault does not protect against malware, clipboard monitoring, screen recording, weak passwords, compromised backups, physical access to an unlocked machine, or plaintext already copied by another tool. Filenames and filesystem metadata may still leak information.

## Legacy Compatibility

Supported legacy formats:

- Text: `Base64(nonce + ciphertext)`.
- File: raw `nonce + ciphertext`.
- AK wrapper: `AK#key#ciphertext`.

Legacy data used `sha256(password)` directly as an AES key. This is supported only for recovery. AK wrappers embed the decryption key in the ciphertext, so parsing is disabled by default and must be enabled only when migrating old data.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m aegisvault
```

For CI/headless smoke tests:

```powershell
$env:AEGISVAULT_HEADLESS_SMOKE="1"
python -m aegisvault
```

## Quality Checks

```powershell
python -m compileall src tests
ruff check .
mypy src
pytest -vv
```

## Package For Windows

```powershell
.\scripts\build_windows.ps1 -Clean
```

The package output is `dist/AegisVault/`.

## Project Structure

```text
src/aegisvault/
  core/          cryptography, KDF, protocol, legacy compatibility
  services/      workflow facade, file IO, recent files
  settings/      persistent settings
  ui/
    components/  reusable widgets
    design/      tokens, spacing and theme
    controllers/ task state and cancellation
    pages/       Text, File, Base64, Settings
tests/
docs/
scripts/
```

## License

MIT. See `LICENSE`.
