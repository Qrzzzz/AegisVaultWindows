# AegisVault 2.8 local acceptance

Baseline: `79c1ea928f4bacd30240b460039a615b29cc2fb5` (2.7). Branch: `codex/aegisvault-2.8`.

Scope: real file-drop acceptance, understandable batch progress, bulk failure actions and consolidated per-file results. The pre-existing deletion of `docs/releases/v1.0.0.md` is excluded.

Status: implementation and local acceptance completed; integrated through [PR #35](https://github.com/Qrzzzz/AegisVaultWindows/pull/35). Standard verification, packaging, full native regression and final focused queue/Explorer checks passed. The user authorized cleanup, push and the formal release flow on 2026-09-12. Remote publication is established by the tag-bound Release workflow and GitHub Release, not by these local checks.

At the user's request, all 21 generated workspace targets were sent to the Windows Recycle Bin on 2026-09-12: 1,688 files, 706,686,381 bytes. This includes local candidates, build/compile caches, test outputs, logs and validation screenshots. Tracked regression sources and fixtures, `.venv` and `web/node_modules` remain. The historical `build/` paths below identify the evidence used during acceptance; those artifacts are now recycled, not retained in the working tree.

Six old empty AegisVault test/audit directory trees and three temporary cleanup/CI log files were also recycled from the user temporary directory. The final release-document check passed all 12 version, source-format and WinUI contract tests without recreating caches.

## Checks

- Standard `scripts/verify_release.ps1`: **passed**. Compileall, Ruff, mypy (28 source files), **394 Python tests**, **82.30% coverage**, and **25 linked-source C# IPC scenarios** passed. Log: `build/2.8-verify.log`; scenarios: `build/ipc-lifecycle/results.jsonl`.
- Added queue regressions use real backend outputs to check filter identity, retained failure reasons, bulk retry without duplicate successful outputs and clearing entries without deleting disk files. A controlled protocol stub checks current-file 50% progress/byte display and live waiting counts independently of queue additions/removals, then cancellation without a claimed result.
- x64 WinUI Release build: **passed**, zero warnings/errors. `scripts/build_windows.ps1 -Zip`: **passed**, including packaged real-backend AGV1/Base64/batch smoke, ZIP/SBOM/checksum generation and artifact audit. Final log: `build/2.8-package-final.log`. Candidate is unsigned; its source metadata refers to the baseline HEAD during local development and is not remote release evidence.
- Native queue runs in **light/en-US** and **dark/zh-CN**, DPI **168**: **passed**. Native multi-selection, duplicate/removal handling, multi-file AGV1 roundtrip, failure filtering, bulk retry preserving successful paths, result expansion and clearing completed entries while retaining outputs were exercised through UI Automation. Dark/Chinese also exercises the bulk command at 680 x 640 physical pixels. Logs: `build/2.8-native-queue.log`, `build/2.8-native-dark.log`.
- **Real Explorer drag/drop passed** through an actual Explorer window and OS mouse input, without calling product drop handlers or using the picker as a substitute. Covered multi-file Text-to-File routing, duplicate suppression, Base64 Text-to-File routing, mixed file/folder and folder-only rejection, appending from Explorer while a 512 MiB Base64 operation remains busy, then safe cancellation with queue retention and no temporary output. Log: `build/2.8-explorer-drop.log`; screenshots: `build/native-evidence/explorer-drop-*.png`. This is automated external drag/drop evidence, not a claim of human manual acceptance.
- Full native suite after harness state-restoration correction: **passed** (`build/2.8-native-full.log`). This covers text/resource/BOM behavior, import/reuse/clipboard/save, file and Base64 roundtrips and collisions, cancellation/temporary cleanup, queues, two-window settings transactions/drafts, localization/theme changes, 680 x 640, accessible settings names, one top-level window and clean cooperative close.
- After the final XAML detail-width refinement, both native queue matrices passed again (`build/2.8-native-final-light.log`, `build/2.8-native-final-dark.log`), including narrow result focus and overflow actions; every real Explorer scenario passed again (`build/2.8-explorer-final.log`). Normal and narrow output-details screenshots in both languages/themes were inspected. The final version/localization/source-format subset passed **12 tests** (`build/2.8-final-contracts.log`); staged whitespace checks and exact `v2.8` metadata validation also passed.

## Reproducing the interactive checks

Run `scripts/test_winui.ps1` with the complete local package available. Set `AEGISVAULT_QUEUE_ONLY=1` for the focused queue matrix, or `AEGISVAULT_EXPLORER_DROP_ONLY=1` for the real Explorer gate; leave both unset for the full suite. The Explorer gate requires an interactive desktop at least 1360 physical pixels wide and creates its own temporary inputs and Explorer window. It closes only that window and restores the app position. Do not interact with the mouse during this opt-in test.

## Corrections and limits

- PR #35 quality and security checks passed. The first post-merge [Quality run](https://github.com/Qrzzzz/AegisVaultWindows/actions/runs/34679153849) hit the existing `file-recent-timeout` test's 10-second `recent-hang` startup-marker wait on Python 3.11; Python 3.12 and 3.13 passed. Re-running the failed source job on the identical commit passed. Production deadlines were unchanged. Final release preparation still requires green packaging and fresh tag-bound verification.
- The first Explorer attempt could not reposition a maximized source window. The harness now restores its own Explorer window before positioning it. A later attempt selected a point inside the item bounds that did not reliably initiate a single-file drag; using the item's UI Automation clickable point passed every external-drop scenario. No production drop workaround was needed.
- The first full suite passed the new queue interactions, then timed out waiting for a Base64 text page because the new test left Base64 in file mode. The test now restores the page and mode expected by subsequent scenarios; the initial log was `build/2.8-native-full-initial.log` and was subsequently recycled with the other test outputs.
- Narrow screenshot review found output details shared too little width with row actions. Details now occupy a separate row spanning the full queue-item width. Final focused native checks and screenshots validate this XAML-only refinement after the full-suite pass; the behavioral implementation is unchanged.
- High Contrast, Narrator and a full multi-monitor/DPI matrix are not newly accepted. AGV1 fixtures, settings schema and Web behavior are unchanged. Queue state remains session-only and passwords are not persisted.
- Local candidates and screenshots are not published release assets. Fresh tag-bound CI, remote digests/provenance and any required signing remain part of a separate formal release.

## Contributor attribution for this version

The user requires Codex in GitHub's native repository Contributors list. GitHub's public API was checked on 2026-09-12: `codex` is a User account (ID `267193182`), and public commits authored with `codex@openai.com` resolve to that login.

The substantive implementation commit [`63f581586017cc71711c2631a64c7f1951f93156`](https://github.com/Qrzzzz/AegisVaultWindows/commit/63f581586017cc71711c2631a64c7f1951f93156) is authored by `Codex <codex@openai.com>` with the configured human committer. PR #35 preserved that commit through merge `cd264b93830fc34edfc6494b8950155b0389421b` into `master`. Historical commits and global Git identity were not rewritten.

After integration on 2026-09-12, the commit API resolved `.author.login` to `codex`; `GET /repos/Qrzzzz/AegisVaultWindows/contributors` returned `codex` (ID `267193182`, one contribution). Native repository contributor attribution is accepted and must remain in the ancestry of the release tag.

Reference: [GitHub contributor requirements](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors).
