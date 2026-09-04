# WinUI 3 review for 2.1

Reviewed on 2026-09-04 before implementation. Baseline: `bd6f5e7` (`master`, released 2.0).
Development branch: `codex/aegisvault-winui-2.1`.

## Cleanup

The initial working tree was clean. No old local `build`, `dist`, screenshots, security reports or
migration logs remained. Six merged local development/release branches were removed with `git branch -d`.
Unmerged local branches, historical release notes/tags, source tests and the development environment were retained.
New comparison evidence is generated under `build/baseline-2.0`; current candidate evidence belongs under
`build/native-evidence`. These generated files are ignored by Git.

The automatic approval layer rejected deletion of this run's synthetic comparison profile with
`blocked by policy`, including a retry with the verified literal path. It remains at
`build/baseline-2.0/91c3977875ce4d40a20702f746e072a3/`; its files are synthetic test data.

## Findings and planned corrections

| Priority | 2.0 finding and evidence | 2.1 correction |
| --- | --- | --- |
| P1 | `WorkflowControl.Run` calls `StartBringIntoView` before result layout settles. Actual 168 DPI Text/File completion screenshots show the Result heading at the bottom with the result itself outside the viewport. Run/Cancel also scroll away with the entire form. | A bounded workflow scroll area with a persistent action/status footer; focus and reveal the result after layout. |
| P2 | All workflow controls share a long vertical form. File browse buttons occupy separate rows, and an inactive Cancel is always shown. Native page headings and body content start at different horizontal positions. | Consistent page heading/description, inline path browsing, contextual decoding options, idle/busy actions and native overflow for result commands. |
| P2 | `Run` clears both password fields even when the two entries do not match; it does not focus the failing field. | Validate before dispatch, preserve correction inputs, focus the failing field, and clear secrets when a task actually starts or its mode/page changes. |
| P2 | `Input`, `InputPath`, `OutputDir` and `IgnoreWhitespace` do not consistently protect busy state or invalidate previous results. Progress callbacks have no task identity guard. | Protect the view-model boundary, invalidate stale feedback on relevant edits, ignore late progress and describe cooperative cancellation. |
| P2 | Copying a file result includes the size summary after its path. Text results cannot be reused as input. | Copy the exact file path; provide text result reuse with the corresponding reverse operation and native adaptive result commands. |
| P2 | Every Settings navigation creates a new draft; Base64 always reopens in text mode. Settings fields are mostly non-notifying auto-properties. “Saved” can remain visible after subsequent edits. | Retain drafts and Base64 input type across navigation, provide save/discard and pending-change feedback, and give recent-history clearing its own feedback. |
| P2 | Existing workflow result/status strings do not retranslate after changing language. | Store message keys and rebuild result metadata when settings are applied. |
| P2 | Native tests check narrow Settings, but not visible workflow actions/results, correction/reuse flows, persisted drafts or language/theme changes in one process. | Extend real native interaction coverage for those behaviors and review fresh screenshots. |

## Scope and validation

Preserve native WinUI 3, the four existing destinations, bilingual resources, system/light/dark themes,
AGV1 compatibility, Python Core/services/settings, locked dependencies and release gates.
This development request does not publish a release.

Run source regression, warnings-as-errors x64 publish, packaged backend/artifact audits and actual native
light/English and dark/Chinese workflows. Record measured DPI and distinguish automated evidence from
High Contrast, Narrator, cross-monitor and user acceptance that have not been measured in this run.

Native command grouping follows Microsoft's [CommandBar guidance](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/command-bar).
Password controls retain the native reveal behavior described in [PasswordBox guidance](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/password-box).

## Implementation outcome

The planned corrections are implemented. Native verification additionally found and corrected command
overflow visibility, the minimal navigation toggle overlapping content, focus/scroll timing that clipped
the result's lower border, and a cached theme label after changing language. Text fields adapt to the
available viewport without reducing fonts. The native harness now waits for actual save completion,
handles both Windows open/save filename controls and verifies localized theme selection.

Current measurements and remaining manual scope are recorded in [UI_ACCEPTANCE.md](UI_ACCEPTANCE.md).
