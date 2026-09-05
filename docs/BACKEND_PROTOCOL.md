# Backend protocol 1

The WinUI client starts its colocated `backend/AegisVault.Backend.exe` with redirected stdin/stdout/stderr,
`UseShellExecute=false` and `CreateNoWindow=true`. Production builds do not consult PATH or environment
variables to locate a backend. Debug builds may use `AEGISVAULT_PYTHON` and an editable Python install.

Transport is UTF-8 JSON Lines. No command-line arguments are accepted by the backend. Passwords, text and
paths are request members on stdin. stdout contains only protocol events; errors contain codes without
exception text. One operation is active per process; the frontend uses one subprocess per call.

```json
{"v":1,"id":"unique-id","op":"text.encrypt","args":{"text":"example","password":"example-password"}}
{"v":1,"id":"unique-id","type":"result","result":{"ciphertext":"AGV1.…","format_name":"aegisvault-v1"}}
```

| Operation | Request members | Result |
| --- | --- | --- |
| `hello` | none | protocol, product version, supported operations, JSON Line and text-limit contract |
| `text.encrypt`, `text.decrypt` | `text`, `password` | ciphertext/plaintext, format_name |
| `file.encrypt`, `file.decrypt` | `input_path`, `password`, optional `output_dir` | input_path, output_path, original_size, output_size, format_name |
| `base64.encode_text` | `text` | text |
| `base64.decode_text` | `text`, optional Boolean `strict`, `ignore_ascii_whitespace` | text |
| `base64.encode_file`, `base64.decode_file` | `input_path`, optional `output_dir` | file result |
| `settings.get` | none | validated persisted settings |
| `settings.update` | changed settings, excluding recent_files | saved settings; invalid candidates are rejected |
| `recent.add` | `input_path` | saved settings; honors history privacy preference |
| `recent.clear` | none | saved settings |
| `cancel` | original request ID | no separate reply; original task emits its terminal event |

Progress events include `percent` in [0,1], `stage`, `detail`, `processed_bytes`, `total_bytes`. Completion
requires a `result` event; a progress value of 1 is not a commit acknowledgment. The Core owns atomic
output commit and rollback. Cancellation after commit may return success. A cancelled operation emits
`{"v":1,"id":"…","type":"cancelled","code":"operation.cancelled"}`; a failed operation emits `type:error`
and a specific Core or IPC error code. Each accepted operation has exactly one terminal event.

The input reader remains available while the worker runs. EOF cancels and joins the worker. The client
waits for process exit after a terminal event; normal window close asks before cancelling active work and
waits for it to stop. A forcibly terminated process or OS crash cannot promise cleanup of temporary files.
KDF work is bounded by the existing Core and does not support interruption within a single derivation.

Maximum request or response line size is 16 MiB including LF. Oversized input produces `ipc.request_too_large` and closes
the service. Duplicate JSON members, non-finite numbers, invalid UTF-8, invalid IDs, Boolean version aliases
and incorrectly typed arguments are rejected. Unsupported protocol versions and unknown operations have
separate error codes. IDs are 1–64 Unicode characters and must be encodable as strict UTF-8; isolated
surrogate code points are rejected before dispatch, while valid non-BMP characters remain supported.
Clients must not send a second operation before the first process has terminated. An oversized response produces
`ipc.response_too_large`; the client terminates and reaps only the backend process tree owned by that request.

## Text resource contract in 2.4

`src/aegisvault/text_limits.json` is packaged into both runtimes. `hello.text_limits` exposes the same values and
the WinUI startup handshake rejects a mismatch. Plaintext accepts at most 1,507,294 UTF-8 bytes and the same
number of .NET UTF-16 code units. Encoded Base64/AGV1 text accepts at most 2,097,152 UTF-8 bytes/code units.
The plaintext value is derived conservatively from the 2 MiB encoded limit, the `AGV1.` prefix, Base64 expansion,
the 64 KiB maximum header, envelope framing and the AES-GCM tag. It also leaves the worst .NET JSON escaping case,
password and request metadata below the 16 MiB line limit.

WinUI `MaxLength`, run preflight, UTF-8 file import, drag/drop and Use Result use the operation-specific values.
The backend repeats the UTF-8 validation and rejects a Base64 or AGV1 input whose decoded plaintext cannot fit the
forward budget. These size checks occur before scrypt when the token shape makes the result size knowable. Valid
non-BMP text remains supported; isolated surrogates remain invalid. The contract changes accepted resource size,
not AGV1 bytes or Base64 semantics.

The client validates numeric response members before conversion. `v` is an Int32 JSON integer;
`processed_bytes`, `total_bytes`, `original_size` and `output_size` are nonnegative Int64 JSON integers.
Fractional, overflowing and incorrectly typed values produce `ipc.invalid_response`. Progress fields are
validated even if a caller does not subscribe to progress.

## Client request lifecycle in 2.3

Cancellation registration and independent supervision are established before the first potentially blocking
pipe write. A cancellation callback only signals state; it never synchronously writes or flushes a pipe. A
background writer serializes the original request and cooperative `cancel` notification, while the cancellation
guard can terminate the exact process tree created by the call without waiting for either write to return.

`hello`, `settings.get`, `settings.update`, `recent.add` and `recent.clear` have a 15-second response deadline.
This covers request write/flush and response reading after a successful process start and leaves room for the backend's existing
five-second settings-lock limit. Text and file operations have no fixed total deadline. User cancellation gives
the backend 30 seconds to emit its terminal event; expiry returns `ipc.cancel_timeout`. An ordinary short-request
expiry returns `ipc.request_timeout`. After a terminal event, stdin is closed and the process has five seconds
to exit before its owned process tree is terminated; reaping and I/O-task settlement have a further five-second
boundary. Cleanup failure returns `ipc.cleanup_failed`. stderr is continuously drained without retaining or
displaying potentially sensitive diagnostics.

Base64 semantics are the existing Core semantics: strict decoding rejects whitespace; relaxed decoding
may ignore ASCII whitespace when requested. Invalid alphabet, padding and non-UTF-8 decoded text still fail.
Configuration persists independently of the UI. The compatibility-only `show_advanced_options` field is
preserved in settings even though WinUI uses a native Expander for advanced options.

## Settings transactions in 2.2

`settings.update`, `recent.add` and `recent.clear` acquire one process-shared OS file lock before loading
the settings used for the change, then validate and atomically save before releasing it. Read-only loads
and text/file/Base64 work do not acquire this lock. The lock acquisition retry loop has a five-second
deadline and observes the operation's cancellation token. Expiry returns `settings.lock_timeout`;
failure to open or acquire a usable lock returns `settings.lock_failed`. No settings are saved in either
case. Cancellation before saving returns `operation.cancelled`; an already committed change can succeed.

The lock uses the persistent empty `.settings.json.lock` sibling, separately from the atomically replaced
JSON file. Ownership resides in an open OS handle; closing the handle or exiting the process releases it.
The sidecar must not be deleted while instances may be running. Only cooperating writers are serialized;
older versions and external editors can still overwrite settings. Low-level `SettingsStore.save` replaces
an explicit snapshot atomically; product read-modify-write callers must use `SettingsStore.update`.

The backend applies supplied `settings.update` fields to the latest persisted snapshot. The current
WinUI `SettingsService.SaveAsync` sends `language`, `theme`, `default_output_dir`, `overwrite_outputs`,
`remember_recent_files` and `show_advanced_options` on every save. Two windows explicitly submitting old
drafts therefore still use last-writer-wins for those fields. Server transaction isolation does not
constitute client draft conflict detection.

Malformed configuration falls back to defaults, including JSON integers rejected by Python's digit
limit. Subsequent `settings.update` can persist a valid replacement; loading alone does not rewrite the
damaged file. Model conversion is outside the JSON parser's exception-recovery boundary.

Base64 file reads bind size and metadata to the opened source handle. Actual bytes read and final handle
metadata are checked before publication; detectable changes return `file.input_changed` and discard
temporary output. Metadata checks are not a strict snapshot against every concurrent edit.
