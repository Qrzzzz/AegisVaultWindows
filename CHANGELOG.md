# Changelog

## 2.1 - 2026-09-04

- Keep workflow actions and feedback visible while input and results scroll; align native page headings and forms.
- Focus visible results after completion, adapt result actions to window width, copy exact file paths and reuse text results as reverse-operation input.
- Preserve password entries for validation corrections, hide inactive cancellation, guard busy input and ignore late progress callbacks.
- Retain Settings drafts and Base64 input type across navigation; add save/discard feedback and retranslate retained workflow status.
- Extend native interaction coverage for narrow layouts, correction/reuse, clipboard, draft persistence and failed settings writes.
- Bound packaged backend smoke failures and clean up bootloader child processes before closing their output pipes.

## 2.0 - 2026-09-04

- Replace the complete Python desktop frontend with C# / WinUI 3 and native Windows App SDK controls.
- Keep the AGV1 Core unchanged; add versioned JSON Lines IPC, progress and cancellation.
- Restore Text, File, Base64 and Settings workflows, bilingual resources and native theme behavior.
- Publish a self-contained x64 folder bundle, with Python and NuGet dependency evidence.
- Adopt two-component product versions; retain four-component Windows PE versions.
- Automated validation and user-reported manual acceptance are recorded in docs/UI_ACCEPTANCE.md.

## 1.2.0 - 2026-09-04

- Implemented the approved modern Windows layout using a Fluent-inspired Qt sidebar, page headings, segmented operations, and responsive password fields.
- Added Light, Dark and system appearance while preserving stored settings and in-progress workspace contents.
- Restored platform-native file and directory dialogs; retained the system window title bar.
- Kept AGV1 and Base64 workflows, atomic writes, cancellation, bilingual controls and accessible keyboard interaction.

## 1.1.0 - 2026-09-04

- Rebuilt the three workspaces as native Windows forms with aligned input, options and result groups.
- Kept the operation between parameters and results, with scrolling content and reachable actions at 600 x 440.
- Preserved the Windows platform light palette instead of replacing it with the generic QStyle palette.
- Added selectable output paths, explicit Tab order and a Base64 file overwrite warning.
- Preserved AGV1, KDF, atomic output protection, cancellation, bilingual settings and previous results.
- Retained PySide6 6.9.3 and the existing dependency locks.

## 1.0.0 - 2026-09-04

- Promoted AegisVault to a stable public `1.0.0` release line with matching package, runtime, display, documentation, script and artifact versions.
- Replaced the decorative desktop shell with fixed-light native Text, File and Base64 tabs, keeping the full workflow and bilingual settings.
- Hardened bounded KDF/protocol parsing, atomic output writes, cancellation and transactional settings persistence.
- Kept the modern protocol compatible with existing `AGV1.` text tokens and `.agv` file containers.
- Preserved AES-256-GCM plus scrypt as the default encryption path for new data.
- Removed all legacy AES text/file decryption, AK wrapper parsing, weak password derivation, recovery dialogs and compatibility settings. Only AGV1 decryption remains supported.
- Removed the archived legacy application from the current source tree; historical commits and published releases are unchanged.
- Split low-level file primitives used by encryption into `aegisvault.core.file_io` so core crypto no longer imports the service layer.
- Standardized the Windows release artifact as `AegisVault-v1.0.0-win64.zip` containing `AegisVault.exe`.
- Added repeatable release verification through `.\scripts\verify_release.ps1 -Build -Zip`.
- Added Python 3.11/3.12/3.13 quality checks, dependency review, pip-audit and CodeQL workflows.
- Added a tag-triggered release workflow that audits the Windows ZIP, SBOM and checksums, attests each public asset and verifies the draft before publication.
- Expanded release consistency tests for stale alpha references, release script parameter compatibility, artifact naming, CI content and release workflow content.
- Rewrote public documentation for security scope, protocol details, unsupported formats, QA and release readiness.

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
