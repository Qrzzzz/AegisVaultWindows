# File batch IPC

Protocol version 1 adds `file.batch` without changing existing operation contracts. `hello` advertises `file.batch` and `max_batch_files: 256`.

```json
{"v":1,"id":"example","op":"file.batch","args":{"operation":"file.encrypt","input_paths":["C:\\data\\first.txt","C:\\data\\second.txt"],"password":"example-only","output_dir":"C:\\output"}}
```

Supported operations are `file.encrypt`, `file.decrypt`, `base64.encode_file`, and `base64.decode_file`. A password is required for the AGV1 operations. An empty/omitted output directory follows the current settings default, then each input directory. The batch snapshots settings once. Passwords travel only through the existing local stdin protocol.

The batch is bounded to 256 unique paths, 32,767 characters per input and 1 MiB of serialized input/resolved/destination path metadata. Shape, Unicode, duplicates, metadata budget and shared options are checked before output creation. A valid request processes ordinary missing, unreadable or invalid files as individual failures and continues in input order. Unexpected internal/transport failures terminate the request with the existing error contract.

Each ordinary progress event uses an aggregate fraction: `(item index + item fraction) / item count`. `batch.item_finished` follows a completed attempt, including failures. A core `done` event can precede atomic publication; only the returned completed item confirms the output.

The terminal result is an object with `cancelled` (boolean) and `items` (array in input order). Each item contains `input_path`, `status`, `code` and `result`:

| Status | Code | Result |
| --- | --- | --- |
| `completed` | Empty | Existing `FileProcessResult` fields: input/output path, original/output size, format |
| `failed` | Existing localized error code | `null` |
| `cancelled` | `operation.cancelled` | `null`; active temporary output cleaned |
| `pending` | Empty | `null`; cancellation prevented the file from starting |

Cancellation uses the existing `cancel` message with the active request ID. The returned batch includes previously completed outputs and unstarted entries. Cancellation before dispatch may use the existing `cancelled` terminal event. EOF still cancels and joins the worker. Batches always disable overwriting for their outputs and select unused names; existing single-file APIs still honor the stored overwrite preference.

The desktop owns an editable in-memory queue, suppresses repeated normalized Windows paths and submits one selected item per `file.batch` request. This intentionally leaves pending items on the frontend so removal and addition during processing take effect without a race with a backend snapshot. It keeps successful outputs when later requests or history updates fail, stops on transport errors, and only retries pending/cancelled entries or explicitly requeued failures. Queue state and passwords are not persisted across application restarts.
