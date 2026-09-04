# AegisVault 2.0 acceptance checklist

Run source checks, actual packaged backend smoke and native UI automation before interactive sign-off.
Do not label any unrun gate as passed. Current evidence is in [UI_ACCEPTANCE.md](UI_ACCEPTANCE.md).

- Preserve the AGV1 fixed text/file fixtures byte for byte; roundtrip binary/Unicode data and empty inputs.
- Confirm wrong passwords, damaged containers and unsupported formats leave no committed plaintext output.
- Exercise Text encrypt/decrypt, import/copy/save; File encrypt/decrypt, native pickers/drop/recent files,
  output folders, collisions, overwrite, progress and cancellation; all Base64 text/file modes.
- Cancel while preparing and streaming; close while busy, decline cancellation, then cancel and close.
  Confirm there is no orphan backend and no partial output after cooperative cancellation.
- Verify settings roundtrip, theme/language application, persistence failure and recent-file privacy.
- Check light, dark, system-following and **real Windows High Contrast**.
- Inspect real 100%, 125%, 150%, 175% and 200% DPI, including moving between monitors.
- Check a narrow window, scrolling, long paths and localized strings without inaccessible controls.
- Use keyboard only: navigation, tab order, Ctrl+Enter, pickers, password reveal, cancel and dialogs.
- Use Narrator: labels, password privacy, error/progress announcements, focus after navigation/dialog close.
- Build x64 Release with zero warnings/errors; audit complete WinUI/runtime/backend ZIP and both dependency ecosystems.
- Separate unsigned local candidates from signed builds, remote CI, attestations and published assets.
