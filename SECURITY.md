# Security Policy

## Supported Versions

AegisVault 1.1.0 is the current stable release, with the same security and format contracts as 1.0.0. Security fixes target the default branch, `master`, and the latest stable release line.

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

## Supported Encryption Formats

AegisVault 1.1.0 decrypts only AGV1 text and file containers. Legacy AES text/files and `AK#key#ciphertext` wrappers are rejected. There is no recovery API, weak legacy password derivation, or setting that enables old-format decryption.

An old settings file cannot re-enable removed functionality. Base64 decoding remains an encoding operation and never invokes a decryptor. Historical releases are not covered by this format-support statement.

## Automated Security Evidence

The `Security` workflow runs dependency review on pull requests and runs pip-audit plus CodeQL on the default branch, on a weekly schedule and on manual dispatch. It retains dependency-review JSON, pip-audit JSON and CodeQL SARIF as machine-readable workflow artifacts.

An advisory is a triage input, not by itself a claim that AegisVault is exploitable. Maintainers must record the affected package and version, whether it is present in the locked runtime closure, the vulnerable code path, AegisVault reachability, mitigations and the upgrade or acceptance decision before describing product impact. Tool errors and unavailable advisory services also fail the gate; they are not vulnerability findings.
