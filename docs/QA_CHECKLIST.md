# QA Checklist

Target version: `0.4.0-alpha`.

## Required Commands

- `python -m pip install -e ".[dev]"`
- `python -m compileall src tests`
- `ruff check .`
- `mypy src`
- `pytest -vv`
- `python -m aegisvault`
- `.\scripts\build_windows.ps1 -Clean`

## Manual UI Smoke

- Launch the app and confirm the shell has Sidebar, PageHeader, Workspace and StatusArea.
- Text page: switch Encrypt/Decrypt and confirm password field only appears for Encrypt.
- Text page: run empty password validation and confirm inline alert appears.
- File page: select a file and confirm metadata, output preview, progress area and cancel button are visible.
- Base64 page: confirm text/file workflows are separated and the encoding-not-encryption warning is visible.
- Settings page: confirm AK compatibility is off by default and has a risk warning.

## Safety Checks

- Wrong passwords fail with a user-readable message.
- Corrupted AGV text/files fail rather than producing output.
- Cancellation removes temporary files.
- Legacy recovery remains compatibility-only.
