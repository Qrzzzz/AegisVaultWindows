# Contributing

Thanks for helping make AegisVault better.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Required Checks

```powershell
python -m compileall src tests
ruff check .
mypy src
pytest -vv
```

## Guidelines

- Keep cryptography and protocol code out of UI modules.
- Treat protocol changes as compatibility events: document them and add tests.
- Do not log plaintext, passwords, derived keys or decrypted content.
- Keep legacy support recovery-only. Do not add new encryption modes that embed keys in ciphertext.
- Prefer small, focused pull requests with clear tests.

