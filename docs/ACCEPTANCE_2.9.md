# AegisVault 2.9 acceptance

## Scope

Reviewed and merged PRs #28, #29, #30 and #31, plus keyboard operation, focus recovery, screen-reader notifications, High Contrast and responsive queue layout. Existing deletion of `docs/releases/v1.0.0.md` is unrelated and excluded.

## Verification

- Four dependency PRs were reviewed as single SHA-pin upgrades and merged to `master`. Combined commit `50c3151f451c7f0a47fb791da66ed04318eb7113` passed the actual Pages build and deploy in run [34734139481](https://github.com/Qrzzzz/AegisVaultWindows/actions/runs/34734139481).
- Python: 394 tests passed; Ruff passed; Mypy passed for 28 source files.
- Linked-source IPC: 25 scenarios passed on retry. The first run hit the existing `file-recent-timeout` / `recent-hang` fixture startup timeout; production deadlines were not changed.
- WinUI x64 Release publish and packaged backend smoke passed. The executable audit verified 2.9 metadata. Local signing status is `unsigned-optional`; this is not a published release.
- Full native regression passed in light/English at actual 168 DPI (175%): Text/File/Base64, boundary imports, password correction, result focus, save/file pickers, collision numbering, cancellation cleanup, settings transactions, language/theme, minimum window and clean shutdown.
- Real High Contrast queue interaction passed in dark/Chinese at 168 DPI; the harness restores the prior Windows setting in `finally`. Screenshots show explicit failure text, system-colour borders/selection and focus indicators.
- Queue keyboard and UIA checks cover filename/state names, full-path help, arrow navigation, Delete restoring next/previous row, Tab/Space activation, failure filtering, bulk retry preserving successes and empty-queue focus. Final targeted checks also cover picker cancellation, Enter on single retry, result-editor Delete safety and narrow-window scrolling.

Local logs and screenshots are under `build/2.9-*.log` and `build/native-evidence/`. Full native regression preceded the final queue-only bring-into-view adjustment; the final targeted queue run validates that adjustment separately.

## Manual release gates

- Narrator: navigate every queue action in Chinese and English; hear filename/state and full path, add/remove/retry/completion/cancellation notifications; confirm byte progress does not interrupt speech and unrelated focus is not stolen.
- High Contrast: the current system contrast scheme is tested; additional light/dark contrast schemes still require manual coverage.
- DPI: 100%, 125%, 150%, 200% and moving between monitors while running; verify all actions remain reachable at minimum window size, long filenames wrap, and both queue and page scrolling work with keyboard.
- Picker cancellation restores its launcher; removal chooses the next/previous row and empty queue chooses Add files; retry chooses password/start; completion must not interrupt a user working elsewhere.

Automated UIA names/events, window resizing and screenshots do not by themselves prove Narrator speech or the physical multi-monitor DPI matrix.
