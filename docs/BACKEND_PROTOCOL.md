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
| `hello` | none | protocol, product version, supported operations, input limit |
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

Maximum request line size is 16 MiB including LF. Oversized input produces `ipc.request_too_large` and closes
the service. Duplicate JSON members, non-finite numbers, invalid UTF-8, invalid IDs, Boolean version aliases
and incorrectly typed arguments are rejected. Unsupported protocol versions and unknown operations have
separate error codes. IDs are 1–64 characters. Clients must not send a second operation before the first
process has terminated. Text UI input is additionally limited to 2,097,152 characters.

Base64 semantics are the existing Core semantics: strict decoding rejects whitespace; relaxed decoding
may ignore ASCII whitespace when requested. Invalid alphabet, padding and non-UTF-8 decoded text still fail.
Configuration persists independently of the UI. The compatibility-only `show_advanced_options` field is
preserved in settings even though WinUI uses a native Expander for advanced options.
