# Changelog

## 1.0.0 - 2026-06-28

- Promoted AegisVault to a stable public `1.0.0` release line with matching package, runtime, display, documentation, script and artifact versions.
- Kept the modern protocol compatible with existing `AGV1.` text tokens and `.agv` file containers.
- Preserved AES-256-GCM plus scrypt as the default encryption path for new data.
- Kept legacy text/file recovery as migration-only compatibility and kept AK parsing disabled by default.
- Split low-level file primitives used by encryption into `aegisvault.core.file_io` so core crypto no longer imports the service layer.
- Standardized the Windows release artifact as `AegisVault-v1.0.0-win64.zip` containing `AegisVault.exe`.
- Added repeatable release verification through `.\scripts\verify_release.ps1 -Build -Zip`.
- Added a tag-triggered release workflow for uploading the Windows ZIP artifact.
- Expanded release consistency tests for stale alpha references, release script parameter compatibility, artifact naming, CI content and release workflow content.
- Rewrote public documentation for security scope, protocol details, migration, QA and release readiness.

## 0.3.0-alpha - 2026-06-28

- Verified editable installation, runtime smoke, linting, typing and tests on Python 3.13.
- Promoted the project positioning to AegisVault as a local Windows encryption and Base64 utility.
- Added protocol, security model and UI specification docs for the AGV1 text token, chunked `.agv` file container, threat boundaries and desktop layout.
- Hardened the Windows packaging script and PyInstaller spec so builds resolve paths from the repository root and include resources, locale JSON and QSS files.
- Added resource QSS files and screenshot placeholder folders expected by the release layout.

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
