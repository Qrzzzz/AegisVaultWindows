# AegisVault

AegisVault 1.0.0 is a local Windows desktop utility for encrypting text and files. It also includes Base64 encode/decode workflows and recovery-only support for selected legacy encrypted data.

The app is offline and local-first. It does not add accounts, cloud sync, telemetry, network features or enterprise key management.

## Who It Is For

AegisVault is intended for users who need a straightforward desktop tool to encrypt local text snippets or files with a password before storing or sharing them. It is not a password manager, endpoint security product or replacement for full-disk encryption.

## Downloads

Stable release artifact:

- `AegisVault-v1.0.0-win64.zip`

Extract the ZIP and run `AegisVault.exe`.

## Features

- Text encryption and decryption with `AGV1.` tokens.
- File encryption and decryption with chunked `.agv` containers.
- AES-256-GCM encryption with scrypt password-based key derivation for new data.
- Base64 text and file encode/decode. Base64 is encoding, not encryption.
- Settings for theme, language, output directory, overwrite behavior, recent files and migration-only compatibility.
- Legacy text/file recovery for supported old data.
- AK wrapper parsing disabled by default because AK wrappers embed key material.
- Atomic output writes for file workflows.

## Security Model

New encryption uses AES-256-GCM and scrypt with random salt. Text tokens authenticate their protocol header as AAD. File encryption is chunked, and each chunk authenticates the header hash, chunk index and final-chunk flag.

AegisVault data is locally encrypted with documented design and tests, but not independently audited.

AegisVault does not protect against malware, clipboard monitoring, screen recording, screenshots, weak or reused passwords, compromised backups, physical access to an unlocked machine, plaintext copied elsewhere, or users losing the password. Filenames and filesystem metadata may still reveal sensitive context.

More detail:

- `docs/SECURITY_MODEL.md`
- `docs/PROTOCOL.md`
- `docs/MIGRATION.md`

## Install From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

```powershell
python -m aegisvault
```

The package also installs the console script:

```powershell
aegisvault
```

For CI/headless smoke tests:

```powershell
$env:AEGISVAULT_HEADLESS_SMOKE="1"
python -m aegisvault
```

## Build A Windows Release

```powershell
.\scripts\verify_release.ps1 -Build -Zip
```

The expected artifact is:

```text
dist\AegisVault-v1.0.0-win64.zip
```

The ZIP contains `AegisVault.exe`.

## Quality Checks

```powershell
python -m compileall src tests
ruff check .
mypy src
pytest -vv
$env:AEGISVAULT_HEADLESS_SMOKE="1"; python -m aegisvault
.\scripts\verify_release.ps1 -Build -Zip
```

## Screenshots

Screenshots can be added under `docs/screenshots/`. The current release keeps a placeholder in that directory so release documentation has a stable path.

## Project Structure

```text
src/aegisvault/
  core/       cryptography, KDF, protocol, legacy compatibility, low-level file primitives
  services/   workflow facade, output naming, recent files
  settings/   persistent settings
  ui/         PySide6 pages, dialogs, components and task controller
  resources/  icon and QSS
scripts/      build and release verification scripts
docs/         security, protocol, migration, QA and release notes
tests/        unit, integration, source-health and release-consistency tests
```

## License

MIT. See `LICENSE`.
