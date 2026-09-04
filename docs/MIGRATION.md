# Format support through 2.2

AegisVault 2.2 preserves the AGV1-only format contract established in 1.x. All legacy decryption and recovery functionality remains removed.

Existing settings remain readable, including `show_advanced_options`. Version 2.2 adds a persistent empty
`.settings.json.lock` beside the JSON file for cooperating settings writers. Its existence does not mean
a lock is held. Keep it in place while instances are running. Older application versions and manual
editors do not participate in this lock; 2.2 does not add conflict detection for explicitly saved UI drafts.

## Supported

- Text tokens beginning with `AGV1.` and containing a valid authenticated AGV1 envelope.
- File containers beginning with the binary `AGVFILE\x01` magic, normally named with the `.agv` suffix.

Existing data in these AGV1 formats remains supported. The encryption format has not been changed by the WinUI migration.

## Not Supported

- Legacy AES text stored as `Base64(nonce + ciphertext)`.
- Legacy AES files stored as raw `nonce + ciphertext`.
- `AK#key#ciphertext` wrappers.

There is no compatibility switch, recovery dialog, hidden fallback or supported recovery API. Settings saved by an older application cannot restore the removed feature. Unsupported ciphertext is rejected without writing a decrypted file.

Changing an extension or adding an `AGV1.` prefix does not convert old data into AGV1. Keep original files and backups intact; this version does not offer in-app migration. The archived legacy application is no longer present in the current source tree. Git history and already-published historical releases remain unchanged.

Base64 tools still encode and decode text or bytes. Base64 is not encryption and never triggers legacy decryption.
