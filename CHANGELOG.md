# Changelog

## 2.8 - Unreleased

- Show current-file percentage and byte progress with separate processed/waiting counts that update during live queue edits.
- Filter failed entries, requeue all failures and clear completed entries without deleting output files.
- Keep file results in expandable queue rows and preserve the separate text result workflow.
- Validate real Explorer drag/drop independently from native picker and queue automation; see `docs/ACCEPTANCE_2.8.md`.

## 2.7 - 2026-09-12

- Add multi-file drag and drop, a native stack of queued files, a multi-select picker, duplicate suppression and per-file removal in the File and Base64 file workflows.
- Keep the queue editable during processing: append files and remove pending items, show individual results, retry failed items, cancel safely and resume unfinished files without repeating successful work.
- Add a bounded `file.batch` backend API for sequential AGV1 and Base64 processing, independent per-file failures, aggregate progress and cancellation results. Batches choose unused output names even when single-file overwrite is enabled.
- Preserve AGV1, text workflows, settings storage and bilingual Windows controls. Local validation is recorded in `docs/ACCEPTANCE_2.7.md`.

## 2.6 - 2026-09-12

- Save only settings fields edited against the draft baseline, preserving other windows' changes, including disabled recent-file history. Same-field edits use the last explicit save (#23).
- Filter invalid Unicode path strings when recovering settings and reject them before runtime persistence, preserving valid history and unrelated preferences (#24).
- Preserve original CR/CRLF, Unicode and NUL in Web results, clipboard API arguments and result reuse through real Workers (#25).
- Validate restored filenames before path joining and collision numbering, keeping successful AGV1/Base64 restore outputs inside the selected directory (#26).
- Consume exactly one UTF-8 BOM on desktop import while preserving subsequent body U+FEFF characters and strict UTF-8/resource checks (#32).
- Local validation and remaining gates are recorded in `docs/ACCEPTANCE_2.6.md`.

## 2.5 - 2026-09-05

- Map malformed UTF-8 backend response lines and truncated UTF-8 at EOF to `ipc.invalid_response` at the reader boundary, retaining cancellation, response limits and process cleanup (#20).
- Add executable IPC regressions for invalid bytes, invalid continuation sequences, truncated EOF and a valid non-BMP response split across the reader buffer with CRLF.
- Revalidate the existing 2.2 repairs for changing Base64 input, malformed settings recovery and process-shared settings transactions (#9, #10, #11); no duplicate replacement of those working implementations.
- Preserve 2.4 text budgets, output naming, AGV1 compatibility, settings schema and privacy preferences. Evidence and remaining gates are recorded in `docs/ACCEPTANCE_2.5.md`.

## 2.4 - 2026-09-05

- Close the text workflow budget in both directions with a shared UTF-8/UTF-16/JSON Line contract. Plaintext is capped at 1,507,294 UTF-8 bytes so worst-case AGV1 output remains within the 2 MiB encoded-text budget; UI input, UTF-8 import, result reuse, client transport and backend validation use the same packaged limits (#12).
- Bound backend response lines to 16 MiB, reject oversized forward or reverse results before expensive work where their decoded size is knowable, and retain complete ASCII, multibyte BMP and non-BMP Unicode roundtrips inside the contract (#12).
- Insert collision numbers before the logical extension chain when creating `.agv` and `.b64` wrappers, so repeated outputs restore as `report (1).txt` instead of `report.txt (1)` without changing non-conflicting names or AGV1 contents (#13).
- Replace target-derived temporary components with fixed 40-character CSPRNG names created through exclusive OS primitives in the destination directory. Atomic flush, overwrite/no-overwrite publication, cancellation/failure cleanup and platform-specific publish behavior remain intact (#14).
- Add boundary, real-backend, linked-client, native workflow, race, long-component and cleanup regressions; pre-release local evidence is recorded in `docs/ACCEPTANCE_2.4.md`.

## 2.3 - 2026-09-05

- Bound backend request lifecycle from the first pipe write through process reaping. Cancellation supervision now starts before potentially blocking I/O, never writes synchronously from a UI cancellation callback, and forcibly reaps only the process tree created for that request (#7).
- Give `hello`, settings and recent-history RPCs a 15-second request deadline while retaining a 30-second cancellation grace period and no fixed total deadline for text or long-running file work. Window initialization, settings operations, workflow cancellation and close now share cancellation signals and restore `IsBusy`/`ActiveTask` on every outcome (#8).
- Preserve a committed file result when the following recent-history update fails, times out or is cancelled, and report that secondary failure as a warning (#8).
- Reject request IDs containing isolated Unicode surrogates before dispatch or settings side effects while retaining valid non-BMP Unicode IDs (#15).
- Validate response version, progress and file-result numeric fields by JSON type and integer range; malformed fault-injection responses consistently return `ipc.invalid_response` instead of leaking `FormatException` (#16).
- Add linked-source C# lifecycle/fault harnesses, real isolated Python protocol regressions and bilingual timeout/cleanup messages; retain detailed local evidence in `docs/ACCEPTANCE_2.3.md`.

## 2.2 - 2026-09-05

- Reject detectable Base64 input changes using opened-handle metadata and actual bytes read; roll back incomplete encoding and decoding output (#9).
- Recover settings containing overlong JSON integers at the parsing boundary without relaxing Python's integer safety limit (#10).
- Serialize settings updates and recent-history changes across cooperating processes for the complete read-modify-save transaction; bound lock waits to five seconds, support cancellation and release locks on process exit (#11).
- Add Chinese/English lock error messages and deterministic file, backend-process and settings-transaction regressions. Preserve AGV1, configuration fields and existing WinUI draft behavior.
- Make packaged smoke use a fresh backend process per operation, matching the client protocol and avoiding a terminal-event/worker-exit race in the test harness.
- Local validation and its remaining manual-test limits are recorded in `docs/ACCEPTANCE_2.2.md`; release artifacts are rebuilt and verified by the tag-bound Release workflow.

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
