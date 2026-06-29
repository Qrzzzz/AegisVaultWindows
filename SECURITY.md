# Security Policy

## Supported Versions

AegisVault 1.0.0 is the supported stable release. Security fixes target the default branch, `main`, and the latest stable release line.

## Reporting A Vulnerability

When the repository is published, please use GitHub Security Advisories or another private maintainer contact path. Do not open public issues with working exploit details before a fix is available.

## Security Boundaries

AegisVault protects data encrypted with a strong user password and the documented AGV1 protocol. Its protection depends heavily on password strength. Short, reused or guessable passwords are vulnerable to offline guessing.

AegisVault data is locally encrypted with documented design and tests, but not independently audited.

AegisVault does not protect against:

- malware or remote-control tools on the same machine,
- clipboard listeners,
- screen recording or screenshots,
- plaintext backups, sync tools or temporary copies made before encryption,
- filenames, timestamps and filesystem metadata,
- weak, reused or leaked passwords,
- users losing the password.

## Legacy Risk

Legacy formats are recovery-only. The old app derived AES keys with `sha256(password)` directly, which is weaker than the current scrypt KDF.

The `AK#key#ciphertext` wrapper is especially risky because the decryption key is embedded in the ciphertext. AegisVault keeps AK parsing disabled by default and labels it as migration-only compatibility.
