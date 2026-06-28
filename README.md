# AegisVault AES

AegisVault AES is a Windows-first desktop encryption app rebuilt from the legacy `AES Encryption System v2.0` script. The 0.2.0-alpha line keeps the legacy recovery path, but the product architecture is now a PySide6 `src/` layout with a documented protocol, tests, CI, settings, packaging files and an MIT license.

The legacy reference script is archived at `docs/legacy/legacy_aes_v2.py`; it is excluded from linting and type checking.

## Project Positioning

AegisVault is intended for local, password-based encryption of text snippets and files. It is not a password manager, cloud sync product, or enterprise key-management system.

## Features

- Modern PySide6 desktop UI with dark Windows 11 styling, Mica backdrop when available, and a stable glass-style fallback.
- Text encryption and decryption with the `AGV1.` token format.
- File encryption and decryption with the `.agv` chunked AES-GCM container.
- Base64 text and file conversion as a separate encoding tool, clearly separated from encryption.
- JSON i18n resources for English and Chinese.
- Drag-and-drop file handling, progress bars, cancellation, output reveal, result summaries and recent files.
- Settings for language, theme, output directory, overwrite behavior, recent files and legacy AK parsing.
- Compatibility decryption for legacy text, legacy files and opt-in AK wrappers.

## Security Design

New encryption uses:

- AES-256-GCM.
- scrypt KDF with per-encryption random salt.
- Strict KDF parameter bounds: scrypt `N` must be a power of two in a safe range, with bounded `r`, `p`, key length and salt length.
- Text tokens authenticate the protocol header as AES-GCM AAD.
- File encryption is chunked. Each chunk has a unique nonce derived from an 8-byte random prefix plus a 4-byte chunk index.
- File chunks authenticate the header hash, chunk index and final-chunk flag as AAD.
- Header size, chunk size and ciphertext record length are bounded to avoid malicious files requesting unbounded memory or CPU.
- File writes use temporary files and atomic replace on success.
- Output files are not overwritten by default.

## What AegisVault Does Not Guarantee

AegisVault does not protect against malware, clipboard monitoring, screen recording, weak passwords, compromised backups, or plaintext already copied by another tool. Filenames and filesystem metadata may still leak information.

## Legacy Compatibility

Supported legacy formats:

- Text: `Base64(nonce + ciphertext)`.
- File: raw `nonce + ciphertext`.
- AK wrapper: `AK#key#ciphertext`.

Legacy data used `sha256(password)` directly as an AES key. This is supported only for recovery. AK wrappers embed the decryption key in the ciphertext, so parsing is disabled by default and must be enabled in Settings when migrating old data.

Large legacy files are guarded by a size threshold because the old raw AES-GCM format cannot be authenticated in a truly streaming-compatible way with the high-level API used by the legacy app.

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

or:

```powershell
aegisvault
```

For CI/headless smoke tests:

```powershell
$env:AEGISVAULT_HEADLESS_SMOKE="1"
python -m aegisvault
```

## Test And Quality Checks

```powershell
python -m compileall src tests
ruff check .
mypy src
pytest -vv
```

The test suite covers modern text and file roundtrips, multi-chunk and empty files, wrong passwords, tampered tokens/files, missing final chunks, trailing data, malicious KDF/chunk parameters, legacy compatibility, AK default-off behavior, Base64 text/files, output naming, settings persistence and i18n key completeness.

## Package For Windows

```powershell
.\scripts\build_windows.ps1 -Clean
```

The build script uses `scripts/aegisvault.spec`, which includes:

- `src/aegisvault/resources/app_icon.ico`
- `src/aegisvault/i18n/locales/*.json`

The package output is `dist/AegisVault/`.

Common packaging failures:

- PyInstaller is not installed: run `python -m pip install -e ".[dev]"`.
- Running outside the repository root: launch the script from `aegisvault-desktop`.
- Missing icon or translation files: verify the `src/aegisvault/resources` and `src/aegisvault/i18n/locales` folders exist.
- Antivirus locking the output folder: remove `dist/` or use `-Clean`.

`pyside6-deploy` may be evaluated later, but PyInstaller is the supported path for this alpha.

## Project Structure

```text
aegisvault-desktop/
  src/aegisvault/
    core/          # cryptography, KDF, protocol, legacy compatibility
    services/      # workflow facade, file IO, recent files
    settings/      # persistent settings
    i18n/locales/  # JSON translations
    ui/
      components/  # reusable widgets
      controllers/ # task state and cancellation
      dialogs/     # About and error dialogs
      pages/       # Text, File, Base64, Settings pages
    resources/     # icon and packaged assets
  tests/
  docs/
    legacy/
  scripts/
```

## Screenshots

Screenshots can be added under `docs/screenshots/` after the first binary release.

## Contributing

See `CONTRIBUTING.md`. Security-sensitive changes should include tests and update protocol documentation.

## License

MIT. See `LICENSE`.

