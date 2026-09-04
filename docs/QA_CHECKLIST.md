# QA Checklist

Target version: `1.1.0`.

## Required Commands

- `.\scripts\install_locked_dependencies.ps1`
- `.\scripts\verify_release.ps1`
- `.\scripts\build_windows.ps1 -Clean -Zip -SigningMode Optional`

The verification script compiles `src`, `tests` and release scripts; runs Ruff, mypy, pytest with XML coverage; and exercises the Qt source smoke with the offscreen platform. The build script performs a clean PyInstaller build, packaged startup smoke, ZIP/PE/resource audit, reproducible CycloneDX generation and checksum verification.

## Manual UI Smoke

- Launch the app and confirm Text, Files, Base64, Settings and About are reachable.
- Text page: encrypt plaintext, decrypt the resulting `AGV1.` token and confirm wrong passwords fail.
- File page: encrypt a small file, decrypt it, confirm progress and reveal-output behavior, and confirm existing outputs are not overwritten unless enabled in Settings.
- Base64 page: confirm the encoding-not-encryption warning is visible and both text/file workflows work.
- Settings dialog: confirm Advanced options contains only the existing overwrite
  setting and its risk warning, with no old-format or embedded-key switch.
- About dialog: confirm version `1.1.0`, repository URL and the AGV1-only
  product boundary are visible.

## Safety Checks

- Wrong passwords fail with a user-readable message.
- Corrupted AGV text/files fail rather than producing output.
- Truncated files, invalid headers, unsafe KDF parameters, oversized headers, chunk corruption, missing final chunks and trailing data fail.
- Cancellation removes temporary files.
- Text/file decryption rejects non-AGV1 contents with a clear localized message:
  only AGV1 is supported; older formats are not supported. Include a static old
  ciphertext and an AK wrapper without a password. Neither should offer a
  recovery action or produce output.
- Static old file bytes remain unsupported even when renamed with an .agv
  extension; no confirmation dialog, plaintext output or temporary file appears.
- Settings save failures leave live settings unchanged; switching tabs or
  language does not rebuild pages or discard input/results.
- Cancel is idempotent; closing waits for worker termination; running tasks
  reject drops that would replace their captured input.
- The release ZIP is named `AegisVault-v1.1.0-win64.zip` and contains `AegisVault.exe`.
- The public release set is exactly the ZIP, `AegisVault-v1.1.0.cdx.json` and `SHA256SUMS`.
- CI signing may be explicitly optional. Publication signing is governed by the repository `AEGISVAULT_SIGNING_MODE` variable and must fail when set to `Required` without a real certificate.
