# AegisVault 2.6 — local acceptance

Baseline: `08a7981a5c3c08345df4ddcd833c9adad908a109` (`origin/master`).
Scope: #23, #24, #25, #26 and #32. Branch: `codex/aegisvault-2.6`.
Status: all five repairs and their local validation passed. This record documents pre-release acceptance; publication is established separately by the annotated `v2.6` tag and successful Release workflow.

## Cleanup

Before implementation, 15 reviewed targets totaling approximately 677 MiB were moved to the Windows Recycle Bin: the merged 2.5 worktree, generated caches/build outputs, Web output and verification screenshots. The obsolete worktree registration was pruned after its directory was recycled. Shared `.venv`, `web/node_modules`, source and formal release history were retained. The pre-existing deletion of `docs/releases/v1.0.0.md` was left as found.

The exact recycled paths are in `build/acceptance-2.6/cleanup.json`. Current validation produces fresh files under `build/acceptance-2.6/`, `dist/`, and `output/playwright/`.

## Repairs and reproducible evidence

- #23: Two production C# `SettingsService`/`SettingsViewModel` instances, linked into the IPC harness and using real Python backend processes, reproduced a theme-only save re-enabling history on the baseline. Saving a field patch against the original draft baseline now preserves unrelated fields, including after a recent-history refresh. Same-field conflicts use the last explicit save.
- #24: Baseline real IPC settings reads returned `file.io_error` for escaped lone high/low surrogates. Loading now filters invalid history strings and restores the default for an invalid output-directory string. Tests retain valid emoji/Chinese entries, update unrelated fields, read persisted settings, and reject invalid runtime values before writing.
- #25: Baseline Chromium/real-Worker tests failed for CR, CRLF and mixed Unicode results, while LF, empty and ASCII controls passed. Raw input/output state now survives copy and repeated processing. Six browser cases cover exact clipboard API arguments, swap/encode, subsequent edits and clear. A real Python-generated AGV1 token is decrypted by the browser Worker, copied and reused for encryption, then decrypted by Python with exact code-point equality.
- #26: Windows real JSONL tests cover both restore formats, explicit/settings/input output directories, invalid boundary names, ordinary and hidden filenames, repeated collisions, original input bytes and temporary-file cleanup. Invalid names are rejected before output creation; successful files remain in the selected directory.
- #32: The production import reader consumes one leading encoding signature, keeping subsequent U+FEFF characters. Linked C# tests cover no BOM, one/multiple BOMs, interior U+FEFF, empty/BOM-only inputs, invalid UTF-8 and the byte boundary, followed by real Base64/AGV1 round trips. Native import validation is recorded below.

## Executed checks

- Python 3.13.14 / locked cryptography 50.0.1: **373 tests passed**, coverage **80.77%**.
- Compileall, Ruff, mypy (27 source files), and whitespace validation passed.
- Web production build, **11 unit tests**, and the final uninterrupted **10 browser tests** passed.
- x64 WinUI/backend build, isolated packaged backend smoke, ZIP/SBOM/checksum generation and artifact audit passed for product **2.6**, PE/assembly **2.6.0.0**.
- All **19 linked-source C# IPC scenarios** passed, including the real-backend import and two-draft settings cases. Process identity checks passed.
- Real packaged WinUI automation passed at DPI 168, initially light/en-US, including BOM import through AGV1 and Base64, invalid restore filenames, native pickers, resource limits, cancellation, collision names and exact output bytes. Two actual windows sharing an isolated settings directory retained disabled history after a stale theme-only save. Theme/language switching, retained drafts, failure/retry, 680 x 640 layout, accessible settings names and both windows' clean shutdown passed. Native screenshots were inspected.

## Test-environment corrections

The first cross-language browser test omitted Python UTF-8 mode, so its synthetic stdin was decoded using the Windows locale. Setting `PYTHONUTF8=1`, as in the existing interoperability test, corrected the harness and the case passed; no production crypto change was needed.

An earlier expanded IPC run passed every scenario but failed the final PID-only process check. The harness now records and compares PID plus process start time, so a subsequently reused Windows PID is not mistaken for a leaked child. This change does not relax the check for the actual owned process.

## Publication and remaining boundaries

The pre-release candidate was unsigned (`unsigned-optional`). Its local SBOM source field used the baseline HEAD and is not release evidence. The authorized release process commits and pushes the candidate, requires PR checks, merges to `master`, and rebuilds from the final annotated tag before verifying and publishing exact assets. The Release workflow and public API state establish the published source and asset binding.

Full High Contrast, Narrator, multi-monitor/DPI coverage and OS-specific clipboard newline behavior are not established by clipboard API argument assertions. The earlier intermittent native COM-finalizer shutdown anomaly is outside these five fixes and is not claimed resolved.

Evidence logs: `build/acceptance-2.6/` (`python-red`, `python-targeted`, `python-full`, `ipc-red`, `ipc-green`, `ipc-final`, `web-build`, `web-unit`, `web-browser`, `web-interop`, `web-browser-final`, `build`, `native`). Failed runs remain available alongside subsequent results. `candidate-manifest.json` records changed-file hashes and the baseline without claiming a new commit.
