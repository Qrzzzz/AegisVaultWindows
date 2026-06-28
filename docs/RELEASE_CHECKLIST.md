# Release Checklist

Target version: `0.4.0-alpha`.

## Before Tagging

- Confirm `pyproject.toml` and `src/aegisvault/__init__.py` versions match the release.
- Run all commands in `docs/QA_CHECKLIST.md`.
- Confirm README describes only verified behavior.
- Confirm `docs/UI_SPEC.md` matches the implemented UI.
- Review `git diff --stat` and exclude unintended generated artifacts from source commits.

## Packaging

- Run `.\scripts\build_windows.ps1 -Clean`.
- Confirm `dist/AegisVault/AegisVault.exe` exists.
- Launch the packaged executable on Windows when doing a binary release.

## Release Notes

- Separate hardening, UI architecture and test changes.
- Call out any known limitations.
- Do not describe legacy recovery or AK compatibility as normal secure encryption.
