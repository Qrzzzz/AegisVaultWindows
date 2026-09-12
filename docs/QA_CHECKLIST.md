# AegisVault 2.6 acceptance checklist

Run source checks, actual packaged backend smoke and native UI automation before interactive sign-off.
Do not label any unrun gate as passed. Current evidence is in [ACCEPTANCE_2.6.md](ACCEPTANCE_2.6.md);
[UI_ACCEPTANCE.md](UI_ACCEPTANCE.md) retains the historical 2.1 UI evidence.

- Link the lifecycle harness directly to this worktree's C# sources. Cover a backend that does not read stdin,
  a read hang, a blocked cancellation notification, a terminal event without process exit, exit/cancel races,
  sustained stderr, independent settings timeout/retry and committed-file/history failure. Give the harness
  its own external timeout and verify every injected process PID is reaped.
- Fault-inject fractional, overflowing and wrongly typed `v`, progress-byte and file-size JSON values. Pass a
  non-null progress observer and require only `ipc.invalid_response`; keep a valid integer control.
- Inject invalid UTF-8 response bytes, invalid continuations and incomplete sequences at EOF. Require
  `ipc.invalid_response` and process cleanup; retain a valid non-BMP response split across the 8192-byte reader buffer.
- In a real isolated Python backend, require isolated high/low surrogate IDs to cause no side effect, one
  deterministic invalid-request response and empty stderr; require a valid non-BMP ID and subsequent request.
- Confirm the production 15-second short-RPC deadline and 30-second cancellation grace, plus the absence of a
  fixed total deadline on file work. Exercise settings cancellation on close and a warning that preserves an
  already committed file when recent-history persistence fails.
- Exercise the shared text limits at one byte below, exactly at and one byte above the plaintext budget with
  ASCII, multibyte BMP and non-BMP Unicode. Require full encrypt/decrypt and Base64 roundtrips, bounded JSON
  serialization, real-backend enforcement, UTF-8 import and successful Use Result for generated outputs.
- Reject an encoded input whose decoded plaintext would exceed the forward budget before generating the large
  result; keep password/empty-value errors, invalid Base64 errors and non-BMP handling unchanged.

- With synthetic files and a second real handle, truncate Base64 input after the first chunk in both directions; require `file.input_changed`, no committed partial output and no temporary residue. Keep static roundtrip, cancellation and no-overwrite controls.
- In an isolated real backend process, test overlong JSON integers, ordinary malformed JSON and valid settings; settings get/update and Base64 must remain usable. Preserve `show_advanced_options` and the interpreter's integer digit limit.
- With two real processes and controlled scheduling, test privacy-off/recent-add, unrelated field updates and recent-clear/update. Wait before the second transaction's load; do not put a two-party barrier inside the lock.
- Confirm a five-second settings lock timeout, cancelled waits, failed writes and process-exit lock release; require subsequent saving to work and no partial JSON. Ordinary crypto operations must not wait for the settings transaction lock.
- Check localized lock failure/timeout messages and retained Settings drafts. Record that explicit old drafts from separate windows still use last-writer-wins for submitted preference fields.

- Preserve the AGV1 fixed text/file fixtures byte for byte; roundtrip binary/Unicode data and empty inputs.
- Confirm wrong passwords, damaged containers and unsupported formats leave no committed plaintext output.
- Exercise Text encrypt/decrypt, import/copy/save; File encrypt/decrypt, native pickers/drop/recent files,
  output folders, collisions, overwrite, progress and cancellation; all Base64 text/file modes.
- Repeat `.agv` and `.b64` wrapping twice and restore both numbered results. Cover multi-dot extensions, hidden
  files, no extension, existing parenthesized numbers and Unicode names; require preserved logical extensions,
  exact bytes, no overwrite and an accurate result when a concurrent writer wins publication.
- Create a legal final component that the old target-derived temporary name would push past the component limit.
  Require success with a fixed-length non-disclosing sibling temp name; require truly illegal targets, injected
  write failures, cancellation, overwrite/no-overwrite and concurrent publication to leave no owned residue.
- Cancel while preparing and streaming; close while busy, decline cancellation, then cancel and close.
  Confirm there is no orphan backend and no partial output after cooperative cancellation.
- Verify settings roundtrip, theme/language application, persistence failure and recent-file privacy.
- Check light, dark, system-following and **real Windows High Contrast**.
- Inspect real 100%, 125%, 150%, 175% and 200% DPI, including moving between monitors.
- Check a narrow window, scrolling, long paths and localized strings without inaccessible controls.
- At 680 x 640 physical pixels, verify visible Run/Cancel and Settings Save/Discard, correction focus,
  and a visible result after layout. Open the native result overflow menu and reuse/save/copy results.
- Navigate away from an edited Settings draft and a Base64 file workflow, then return. Discard changes;
  simulate a locked settings file, verify no persisted/applied change, unlock and save the retained draft.
- Use keyboard only: navigation, tab order, Ctrl+Enter, pickers, password reveal, cancel and dialogs.
- Use Narrator: labels, password privacy, error/progress announcements, focus after navigation/dialog close.
- Build x64 Release with zero warnings/errors; audit complete WinUI/runtime/backend ZIP and both dependency ecosystems.
- Separate unsigned local candidates from signed builds, remote CI, attestations and published assets.
