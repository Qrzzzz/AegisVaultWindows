# Security Model

AegisVault 1.0.0 protects local text and files after they are encrypted with a strong user password and the modern AGV1 protocol.

AegisVault data is locally encrypted with documented design and tests, but not independently audited.

It does not protect against malware, remote-control software, clipboard monitoring, screen recording, screenshots, weak or reused passwords, plaintext already copied elsewhere, compromised backups, physical access to an unlocked machine, or users losing the password.

## Passwords

Passwords are never stored by AegisVault. Modern encryption derives AES keys with scrypt and a random salt. Weak passwords remain vulnerable to offline guessing, especially if an attacker obtains the encrypted file or token.

## Modern Encryption

New text and file encryption uses AES-256-GCM. Text tokens authenticate the protocol header as additional authenticated data. File containers encrypt in chunks, and each chunk authenticates the header hash, chunk index and final-chunk flag.

## Metadata

Encrypted file contents are protected. Filenames, output paths, timestamps, file sizes and backup metadata can still reveal information. Users should rename sensitive files before or after encryption when filenames are sensitive.

## Local Threats

AegisVault is a local utility, not an endpoint security product. If the machine is already compromised, attackers may capture plaintext, passwords, screenshots or clipboard data before encryption or after decryption.

## Legacy Formats

Legacy formats are migration-only. They use weaker key derivation and should be re-encrypted into the modern AGV1 format immediately after recovery. AK wrappers are disabled by default because they place key material next to ciphertext.

## Temporary Files

Modern write workflows use same-directory temporary files and atomic replace on success. Failure and cancellation paths try to remove temporary files. If the operating system blocks cleanup, the user should delete the leftover `.tmp` file after confirming the operation failed.
