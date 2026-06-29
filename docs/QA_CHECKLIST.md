# QA Checklist

Target version: `1.0.0`.

## Required Commands

- `python -m compileall src tests`
- `ruff check .`
- `mypy src`
- `pytest -vv`
- `$env:AEGISVAULT_HEADLESS_SMOKE="1"; python -m aegisvault`
- `.\scripts\verify_release.ps1 -Build -Zip`

## Manual UI Smoke

- Launch the app and confirm Text, Files, Base64, Settings and About are reachable.
- Text page: encrypt plaintext, decrypt the resulting `AGV1.` token and confirm wrong passwords fail.
- File page: encrypt a small file, decrypt it, confirm progress and reveal-output behavior, and confirm existing outputs are not overwritten unless enabled in Settings.
- Base64 page: confirm the encoding-not-encryption warning is visible and both text/file workflows work.
- Settings page: confirm AK compatibility is off by default and has a risk warning.
- About dialog: confirm version `1.0.0`, repository URL and migration notes are visible.

## Safety Checks

- Wrong passwords fail with a user-readable message.
- Corrupted AGV text/files fail rather than producing output.
- Truncated files, invalid headers, unsafe KDF parameters, oversized headers, chunk corruption, missing final chunks and trailing data fail.
- Cancellation removes temporary files.
- Legacy recovery remains compatibility-only.
- AK wrappers remain disabled by default.
- The release ZIP is named `AegisVault-v1.0.0-win64.zip` and contains `AegisVault.exe`.
