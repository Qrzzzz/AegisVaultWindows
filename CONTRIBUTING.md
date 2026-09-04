# Contributing

Thanks for helping make AegisVault better.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
.\scripts\install_locked_dependencies.ps1
# Install the .NET SDK in global.json, then:
.\scripts\run_dev.ps1
```

## Required Checks

```powershell
python -m compileall src tests
ruff check .
mypy src
pytest -vv
.\scripts\build_windows.ps1 -Clean -Zip
.\scripts\test_winui.ps1
```

## Guidelines

- Keep cryptography and protocol code out of UI modules.
- Treat protocol changes as compatibility events: document them and add tests.
- Do not log plaintext, passwords, derived keys or decrypted content.
- Keep decryption AGV1-only. Do not restore removed formats or embed keys in ciphertext.
- Use native WinUI controls and keep all cryptographic work behind the documented JSON Lines protocol.
- Prefer small, focused pull requests with clear tests.
