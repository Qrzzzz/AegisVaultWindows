# Release Checklist

Target version: `1.0.0`.

## Before Tagging

- Confirm `pyproject.toml`, `src/aegisvault/version.py`, `src/aegisvault/__init__.py`, README, SECURITY, CHANGELOG, QA checklist and release notes all reference `1.0.0`.
- Run all commands in `docs/QA_CHECKLIST.md`.
- Confirm README describes only verified behavior.
- Confirm `docs/UI_SPEC.md` matches the implemented UI.
- Review `git diff --stat` and exclude unintended generated artifacts from source commits.

## Packaging

- Run `.\scripts\verify_release.ps1 -Build -Zip`.
- Confirm `dist\AegisVault.exe` exists.
- Confirm `dist\AegisVault-v1.0.0-win64.zip` exists.
- Confirm the ZIP contains `AegisVault.exe`.
- Launch the packaged executable on Windows when doing a binary release.

## Tagging

- Create tag `v1.0.0`.
- Push the tag to trigger the release workflow.
- Confirm the uploaded artifact is `AegisVault-v1.0.0-win64.zip`.

## Release Notes

- Use `docs/releases/v1.0.0.md` as the source.
- Call out known limitations.
- Do not describe legacy recovery or AK compatibility as normal secure encryption.
