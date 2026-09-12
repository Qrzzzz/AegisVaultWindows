# AegisVault 2.7 local acceptance

Status: local implementation and automated acceptance completed; publication authorized on 2026-09-12. Automated source, IPC, packaging and native picker/queue checks passed. Real mouse drag/drop remains manually unverified; the checks below do not constitute remote release evidence.

Baseline: `37a356c278f7b9f1b2d8d0bb9416d3c3a3f84978`. Working branch: `codex/aegisvault-2.7`.

Scope: multi-file drop/selection, editable File and Base64 file queues, batch backend processing, progress, partial failures, retries, cancellation/resume and bilingual native UI. The pre-existing local deletion of `docs/releases/v1.0.0.md` is excluded from this release change.

## Implemented behavior

- File and Base64 file workflows use a native scrollable queue, multi-select picker, normalized-path duplicate suppression, individual removal and status, failure retries and retained output paths. The queue accepts additions/removals of waiting files while a run is active. The running file stays fixed.
- A run snapshots its operation, password and destination rule. A later default-folder change from another settings writer cannot redirect that run. Cancellation retains committed results and unfinished work; starting again does not repeat completed files. Result actions no longer displace Cancel in the footer while results accumulate.
- `file.batch` supports bounded lists for AGV1 and Base64 file operations, per-file failure isolation, cancellation results and aggregate progress. It preserves input files and numbers conflicting output names even when the single-file overwrite preference is enabled. Details are in `BATCH_IPC.md`.
- Window-level storage drops route Text/File pages to the File queue and Base64 pages to the Base64 file queue. This wiring compiles; the physical mouse/Explorer path is explicitly unverified below.

## Executed checks

Log and screenshot paths below identify the evidence inspected before cleanup. On 2026-09-12, the user requested that temporary test files, intermediate outputs and verification screenshots be moved to the Recycle Bin; those artifacts are no longer in the workspace. The recorded outcomes and limitations remain here, and release CI produces fresh evidence from committed source. After release-document updates, the final version/source-format/WinUI contract subset passed 12 tests; tag metadata and whitespace checks also passed.

- **394 Python tests passed**, overall coverage **82%**, including 21 batch cases for AGV1/Base64 round trips, missing/invalid files, wrong passwords, collision/input protection, cancellation cleanup, invalid requests, duplicate paths, metadata limits and real backend processes. Log: `build/2.7-python-final.log`.
- Ruff, mypy (**28 source files**), compileall and whitespace checks passed. The final version/localization/source-contract subset passed **17 tests**. Logs: `build/2.7-ruff-final.log`, `build/2.7-mypy.log`, `build/2.7-contracts-final.log`.
- **22 linked-source C# IPC scenarios passed** in the final serialized run. New cases cover live queue additions/removals, immutable running options, a default-directory change during a run, retry/resume without repeated outputs and malformed batch responses. Existing history-failure tests also assert that result actions stay hidden and cancellation remains available while busy. Log: `build/2.7-ipc-serial-final.log`.
- x64 WinUI Release build passed with **zero warnings/errors**. The packaged backend passed existing smoke plus real multi-file AGV1 encryption/decryption and a Base64 partial-failure batch. ZIP, SBOM, checksum generation and local artifact audit passed for product **2.7**, PE/assembly **2.7.0.0**. Log: `build/2.7-package-accepted.log`.
- The full native WinUI suite passed at **DPI 168**, starting light/en-US. It covers existing text/resource/BOM behavior, file round trips, native pickers, cancellation cleanup, multi-file selection, duplicate suppression, per-item removal, batch AGV1 round trips, copied paths, Base64, collision names, long filenames, settings transactions, two-window drafts, language/theme switching, 680 × 640 layout, accessible settings names and cooperative window close. Log: `build/2.7-native-accepted.log`.
- A separate final **dark/zh-CN** queue run passed native multi-selection, duplicate/removal behavior, batch round trips and clean shutdown. Light/English and dark/Chinese queue screenshots were inspected. Log: `build/2.7-native-queue-dark.log`; screenshots: `build/native-evidence/queue-pending-*`, `queue-narrow-*`, `queue-completed-*`.

## Test corrections and retained failures

- The default PATH contained only a .NET runtime. The required **10.0.400** SDK was downloaded from Microsoft's release feed, SHA-512 checked and expanded into `C:/Users/qrzzz/.cache/aegisvault-dotnet/10.0.400`, without changing system PATH.
- Extending packaged smoke from six to nine backend calls required updating its lifecycle trace assertion. The existing fresh-process/exit invariant is still checked for every call.
- Native multi-selection initially entered several full paths into the filename field, exceeding that control's usable entry length. The harness now navigates to the common directory and enters quoted leaf names; it also uses this path for long filenames. No production picker workaround was introduced.
- The first full native close test missed busy state when result commands occupied the narrow command bar. Result actions now stay hidden while busy, and the close test observes the disabled operation selector before closing. The final full suite passed.
- One IPC run made concurrently with native automation timed out waiting for the `recent-hang` stub marker. The unchanged scenario and new assertions passed in the final serialized run. No production deadline was relaxed. The earlier failure and final success were recorded before the requested cleanup.

## Remaining acceptance and publication boundaries

The experimental OLE/mouse harness could not establish a successful external drag. In its mouse-driven variant the drag source did not receive the injected mouse press. Those failed probes were recorded in `build/2.7-native-queue-*.log` before cleanup; their temporary injection implementation was removed from the test suite. Native picker success and view-model queue tests are **not** counted as real Explorer drag/drop evidence. Manually verify multiple-file drop, Text/Base64 automatic routing, folder rejection and additions during a running batch using `QA_CHECKLIST.md`.

High Contrast, Narrator and a full multi-monitor/DPI matrix were not newly accepted. Queue state is intentionally session-only.

The pre-release candidate was unsigned (`unsigned-optional`), and its local SBOM referenced the baseline HEAD. It was not uploaded as a release artifact. The authorized publication path is commit/push, PR checks, merge, annotated `v2.7`, then a fresh build and digest/provenance verification by the Release workflow. Successful CI does not change the manual-acceptance limits above.

The cleanup moved 26 reviewed targets (1,974 files, 905,813,612 bytes) to the Recycle Bin: local build/package outputs, prior candidate ZIPs, test caches, logs, screenshots, .NET bin/obj folders, Web outputs and two synthetic IPC profiles from this run. Formal regression sources/fixtures, the Python environment and installed dependencies were retained.

For traceability only, the recycled local candidate ZIP had SHA-256 `4c1f38bdc9565166e483d129e460a91fe63df263d00a3882aa5123d897451c8e` (99,125,490 bytes). This is not a digest for the final GitHub Release asset.
