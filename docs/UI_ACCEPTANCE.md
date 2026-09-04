# AegisVault 2.1 — acceptance evidence

Status: **local candidate validated; maintainer authorized release** on 2026-09-04.
The maintainer requested "release" for the pushed candidate `21e8163`, authorizing publication using
the recorded native validation. No additional per-scenario manual test results were supplied.
Remote quality/security checks, tag binding and artifact provenance remain required before publication.
Baseline: released 2.0 at `bd6f5e7`. Review: [UI_REVIEW_2.1.md](UI_REVIEW_2.1.md).

2.0 was rebuilt and its existing native light/English suite passed before implementation, at 168 DPI
with High Contrast disabled. The comparison screenshots confirmed that completed results were below
the visible area despite the previous suite passing.

Current evidence is generated under `build/native-evidence`; the tests use isolated profiles and synthetic
inputs and restore the clipboard after exercising copy. Large synthetic fixtures are removed when a run ends.
The new native coverage exercises correction/focus, visible narrow-window actions/results, text reuse,
clipboard/save picker, output invalidation, draft retention/discard and a real locked-file save failure/retry.

| 2.1 check | Measured result |
| --- | --- |
| Python source gate | 246 tests passed; 76.48% coverage; compileall, Ruff and mypy passed; final UI/version contract checks passed |
| WinUI build/publish | x64 Release, locked restore and warnings-as-errors passed; PE `2.1.0.0`, product `2.1` |
| Packaged backend and bundle | AGV1 text/file and Base64 smoke passed with isolated profile/minimal PATH; input-root, PE/runtime, ZIP, SBOM and checksum audit passed |
| Packaged smoke failure lifecycle | Real child processes are stopped after a backend error or request deadline; continuing progress cannot extend the deadline; stderr flooding and early exit report a failure without blocking |
| Native light/English and dark/Chinese | Text/file/Base64 roundtrips, correction focus and password clearing, reverse-result reuse through narrow command overflow, text/path clipboard and native open/save pickers passed |
| Native state and lifecycle | Destination edits invalidate results; Base64 mode and Settings drafts survive navigation; discard, real failed settings write/retry, theme/language application, localized theme selection and status translation passed |
| Native narrow layout | 680 x 640 physical pixels at **168 DPI / 175%**; fixed Run/Cancel and Settings actions, content below the navigation toggle, result focus/scrolling and screenshots reviewed |
| Accessibility and close | 13 focusable narrow Settings elements have names; Ctrl+Enter, cooperative cancellation, ContentDialog close and clean exit passed; one top-level app window at rest |
| Scope preservation | No changes to Python Core, services, settings or dependency locks |

Evidence files:

- `build/validation-2.1/source-checks.log`, `build/validation-2.1/contracts.log`
- `build/validation-2.1/source-release-final.log`, `build/validation-2.1/smoke-lifecycle.log`, `build/validation-2.1/packaged-smoke-final.log`
- `build/validation-2.1/package.log`
- `build/validation-2.1/native-light.log`, `build/validation-2.1/native-dark.log`
- `build/native-evidence/*.png` (actual native screenshots, including the intentional settings-write failure)
- `dist/AegisVault/AegisVault.exe`, `dist/AegisVault-v2.1-win64.zip`, `dist/AegisVault-v2.1.cdx.json`, `dist/SHA256SUMS`

High Contrast was disabled during automation. Other DPI scales, cross-monitor behavior, Narrator, drag/drop,
folder pickers and a Windows 10/11 device matrix were not independently exercised in this run. The candidate
is unsigned. These local checks do not establish remote CI, PR, tag or Release status; publication remains
separate release work.

The historical 2.0 sign-off below applies only to 2.0 and is not acceptance of this candidate.

## Historical 2.0 evidence

Status: **user-reported manual acceptance passed; release authorized** on 2026-09-04.
The maintainer's instruction was “验收通过；开始release”. This closes the manual acceptance stage;
it does not turn unmeasured scenarios into automated test results.
The migration baseline is `master` at `1a74984` (1.2.0), developed on `codex/aegisvault-winui-2.0`.
Remote CI, tag/source binding, artifact audits and provenance remain enforced by the release workflow.

## Completed evidence

| Check | Result |
| --- | --- |
| Pre-migration Core baseline | 171 tests passed, including byte-exact AGV1 text/file fixtures |
| Core preservation | No diff in `src/aegisvault/core`, `services` or `settings` |
| Full Python suite | 243 passed; coverage 76.48%; compileall, Ruff and mypy passed |
| JSONL subprocess tests | 21 passed: fixed 1.x token, text/file/Base64, strict validation, oversized input, argv rejection, cancellation/EOF cleanup and settings privacy |
| x64 Release | Solution build completed with 0 warnings and 0 errors; publish uses warnings-as-errors and locked NuGet restore |
| Packaged backend | AGV1 text/file and Base64 smoke passed with isolated profile, working directory and minimal PATH |
| Package inspection | x64 PE/version, WinUI PRI/runtime, backend archive, no retired GUI dependencies, exact ZIP bytes, mixed-runtime SBOM and checksums passed |
| Dependency advisory scans | pip-audit and NuGet transitive scan reported no known vulnerable dependencies |
| Native light / English | Actual `WinUIDesktopWin32WindowClass`, Ctrl+Enter, text/file roundtrips, Windows App SDK file picker, Base64 text/file, cancellation cleanup, settings and narrow layout passed |
| Native dark / Chinese | Same workflows passed, plus ContentDialog close during a task, cooperative shutdown and clean process exit |
| Native DPI | **168 DPI / 175%** measured with GetDpiForWindow |
| Window lifecycle | One app top-level window at rest; native modal close dialog; no partial file after cooperative cancellation |
| Accessible controls | Native labels and automation IDs; 14 focusable Settings controls had nonempty accessible names; keyboard primary action exercised |
| Visual review | Real window screenshots reviewed in light/English, dark/Chinese, narrow Settings and close dialog; no web or Qt rendering |

The test harness starts the **published** executable, uses synthetic inputs and an isolated profile,
and restores no production user settings. The filesystem/package tests do not depend on installed Qt.
The `.NET 10.0.400` SDK used locally is isolated under `%LOCALAPPDATA%/AegisVaultBuild/dotnet`.

## Evidence locations

- `.migration-final-verify.log`: complete source gate, clean package, isolated smoke and package audit.
- `.migration-final-build.log`: solution build with zero warnings/errors.
- `.migration-final-package.log`: final folder/ZIP rebuild after version-display synchronization.
- `.migration-native-picker.log`: English/light native workflows and actual file selection.
- `.migration-native-dark-final.log`: Chinese/dark workflows and close dialog lifecycle.
- `build/native-evidence/*.png`: real-window screenshots from the UI Automation test harness.
- `security-reports/pip-audit-2.0.json`, `security-reports/nuget-audit-2.0.json`: advisory reports.
- `dist/AegisVault/AegisVault.exe`: runnable complete application folder.
- `dist/AegisVault-v2.0-win64.zip`, `dist/AegisVault-v2.0.cdx.json`, `dist/SHA256SUMS`: local unsigned candidate.

Logs, reports and built artifacts are generated local evidence, not source-controlled release claims.

## Manual acceptance scope and evidence limits

- The maintainer accepted the native UI for release. No individual manual test transcript was supplied.
- High Contrast, DPI 100%–200%, cross-monitor/text scaling, Narrator and full keyboard operation were part
  of the requested acceptance scope. Automated evidence above measures 175% with High Contrast disabled;
  the general manual sign-off is recorded separately and is not a per-scenario measurement.
- Folder/save pickers, clipboard and drag/drop rely on the manual sign-off; automated interaction exercised
  the native file-open picker, accessible names and Ctrl+Enter.
- The local package is unsigned. Actual release signing status follows the configured Optional/Required
  policy and must be reported from the release build. No certificate or Windows 10/11 test matrix is inferred.

## Remote release evidence

The pull request must pass Quality and Security before merge. The annotated `v2.0` tag must bind the exact
default-branch commit. The Release workflow builds on a clean Windows runner, audits the full package,
attests the three public assets and verifies downloaded draft assets before publication. The public release
and its workflow run provide the final remote record; the local logs above are not substitutes.
