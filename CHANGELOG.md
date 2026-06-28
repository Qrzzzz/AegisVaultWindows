# Changelog

## 0.2.0-alpha - 2026-04-28

- Moved the releasable repository into the ASCII-friendly `aegisvault-desktop` root.
- Archived the legacy script as `docs/legacy/legacy_aes_v2.py`.
- Split the PySide6 UI into pages, dialogs, components and a task controller.
- Added unified task states: idle, running, cancelling, cancelled, failed and done.
- Added independent Base64 file result/progress UI.
- Added strict KDF, header, chunk-size and chunk-record limits.
- Added legacy file size guard.
- Added PyInstaller spec file.
- Expanded tests for tampering, malicious parameters, legacy/AK behavior, Base64 files, settings and i18n.

## 0.1.0 - 2026-04-28

- Rebuilt the legacy AES tool as a PySide6 desktop application.
- Added AegisVault v1 `AGV1` text format and `.agv` chunked file container.
- Added scrypt password derivation.
- Added legacy text/file/AK compatibility decryption.
- Added settings, JSON i18n, tests, CI, packaging script and MIT license.

