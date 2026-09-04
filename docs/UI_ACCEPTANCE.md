# Modern Windows UI acceptance

Date: 2026-09-04. UI acceptance evidence for AegisVault 1.2.0.

## Implemented

- Fluent-inspired Qt Widgets shell with a system title bar, sidebar navigation,
  responsive icon rail and three persistent workspaces.
- Page headings, exclusive operation switches, responsive password fields,
  file drop areas, output-path cards and results shown after processing.
- Light, Dark and system appearance, applied through transactional settings
  saves without replacing pages or losing inputs, passwords or previous results.
- Platform-native file/folder dialogs, localized accessible control names,
  keyboard shortcuts, and reachable operations at 600 x 440 logical pixels.

This implementation uses PySide6/Qt, not WinUI or an embedded browser.

## Validation

The project-pinned dependencies were installed with hash verification into an isolated runtime. The acceptance below uses the pinned
PySide6/Qt **6.9.3**.

- Full suite: **275 passed**.
- Windows platform (`QT_QPA_PLATFORM=windows`) workflow and modern UI tests:
  **11 passed**, including real file cancellation/close cleanup, keyboard
  operation selection and transactional appearance saves.
- Ruff passed; mypy passed for all 50 source files; `git diff --check` passed.
- Windows capture/exercise runs in both Light and Dark completed AGV1 text and
  file round trips, Base64 text and file round trips, authentication failure,
  and language changes with results retained. The Windows system DPI observed
  during capture was **1.75**. Screenshots cover Chinese/English and default,
  900 x 680 and 600 x 440 logical sizes.
- Maintained 1024 x 760 offscreen screenshots were regenerated and visually
  reviewed, including the input, result and settings states.
- PyInstaller input-root audit passed for **552 absolute paths**.
- The packaged executable passed isolated startup with a minimal Windows PATH
  and exit code **0**. This is a startup smoke test; the real workflow tests
  above execute the source application using the locked runtime.

The Windows interaction checks use Qt's test driver and synthetic data, not
manual acceptance by a person. No real passwords or user files were used.

## Release and cleanup

The tag workflow rebuilds version 1.2.0, audits the package, and verifies the
three public assets and their provenance before publication. The earlier
working-tree trial executable is not a release artifact. Temporary captures,
trial builds and local validation logs are disposable; the five maintained
visual regression baselines remain part of the test suite.
