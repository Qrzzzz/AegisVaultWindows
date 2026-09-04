# AegisVault 2.3 — local acceptance evidence

Status: **local acceptance complete**, 2026-09-05. Acceptance was completed before commit, PR, tag and Release;
those remote publication records are separate evidence and are not inferred from the local results below.

## Source and baseline

- Worktree started clean at detached `553344d092328d251c210b340a6ab062e6399c97`, the merge commit for PR #17.
  `origin/master` resolved to the same SHA and GitHub Release v2.2 targets it.
- The baseline contains the 2.2 Base64 source-change, damaged-settings and cross-process transaction fixes.
  No source or build output from the older `2dd5459` audit worktree was used as the 2.3 implementation.
- Reused audit harness source was copied into `build/2.3-baseline/`, rebuilt with links to this worktree's
  baseline sources, and run only for before-fix evidence. Its old binaries and measurements were not reused.

Before the change, the rebuilt harness demonstrated:

- #7: with a backend that never read stdin, cancellation had still not completed after 32 seconds; it completed
  only after the harness killed its own recorded stub PID.
- #8: `settings.get` retained `IsBusy=true` with an incomplete `ActiveTask`; after a real Python Base64 file
  commit, a hung `recent.add` kept workflow/settings busy and close-wait incomplete until the harness killed its
  own stub. The source path contained no request deadline or settings cancellation token.
- #15: isolated high and low surrogate IDs saved `theme=dark`, emitted no matching terminal response, and wrote
  `UnicodeEncodeError` to stderr; a following healthy request succeeded. The process exited only after EOF.
- #16: fractional and overflowing `v` and `processed_bytes` values escaped as `FormatException`; a string `v`
  control was already mapped to `ipc.invalid_response`.

The finite observations above are paired with the inspected source paths; they are not presented as proof by
waiting alone. Baseline logs are under `build/2.3-baseline/`.

## Lifecycle and deadlines

- A call registers cancellation, starts stderr draining and creates independent supervision before scheduling
  the first stdin write. The UI cancellation callback only completes a task signal. Original and cancellation
  writes are serialized in background code; the supervisor can kill the exact `Process` tree without waiting
  for a blocked write task.
- `hello`, settings and recent-history RPCs have a 15-second transport deadline after successful process start. This exceeds the 2.2
  settings lock's five-second deadline. Text and file operations deliberately have no fixed total deadline.
- User cancellation has a 30-second cooperative grace period. Short-request expiry is `ipc.request_timeout`;
  cancellation grace expiry is `ipc.cancel_timeout`; premature exit is `ipc.backend_exited`; malformed response
  is `ipc.invalid_response`; failed bounded reaping is `ipc.cleanup_failed`.
- A terminal process gets five seconds to consume EOF and exit before tree termination, then five seconds for
  reaping and I/O task settlement. stdin is closed through its raw stream so StreamWriter disposal cannot add a
  second unbounded flush. Every background task has an exception observer and bounded join path.
- Tests inject shortened deadlines of five seconds or less, with hosted-runner cold-start headroom, and assert the
  production 15/30/5/5-second policy separately. A delayed file response outlives an independent 100 ms short-RPC
  deadline, proving file operations do not inherit it.

## Issue-to-validation map

| Issue | Implementation | Candidate evidence |
| --- | --- | --- |
| #7 | `BackendClient` background transport, pre-I/O cancellation signal, independent deadline/kill and bounded cleanup | Request-write block, cancellation while the original write holds the gate, response-read hang, terminal-without-exit, exit/cancel race and owned-PID reaping all pass |
| #8 | Short RPC deadlines; cancellable `SettingsService`; initialization/close token propagation; recent-history as a secondary file step | Independent settings timeout restores busy state and retry succeeds; real Python file remains byte-correct after `recent.add` timeout and cancellation; warning/result state and process exit pass |
| #15 | Strict UTF-8 request-ID validation before dispatch | Real isolated Python subprocess rejects both surrogate halves with `id:null`, no settings file/side effect, one terminal response, empty stderr and healthy continuation; non-BMP `healthy-🔐` control passes |
| #16 | Explicit JSON kind/range readers for envelope, progress and file results | Fractional, Int32/Int64 overflow and wrong types for `v`, `processed_bytes` and `total_bytes` all become `ipc.invalid_response`; non-null progress observer and valid integer control pass |

## Executed validation

- `scripts/verify_release.ps1`: passed compileall, Ruff, mypy, **305 Python tests**, 79.34% coverage, and the
  linked-source IPC lifecycle suite.
- `scripts/test_ipc_lifecycle.ps1`: passed 11 bounded scenarios. The script builds both C# projects from source,
  uses an external 120-second runner deadline, records each injected PID and only tree-kills its own runner/stubs.
- WinUI x64 Release build: passed with locked restore, warnings as errors, .NET SDK 10.0.400.
- `scripts/build_windows.ps1 -Clean -Zip -SigningMode Optional`: passed backend input-root audit, packaged hello,
  AGV1 text/file and Base64 smoke, WinUI/backend artifact audit, ZIP/SBOM generation and exact 2.3 metadata.
- Real packaged native UI Automation passed twice: light/en-US and dark/zh-CN. Each covered normal startup,
  text/file/Base64 roundtrips, a 512 MiB file cancellation with partial cleanup, cancel-and-close ContentDialog,
  native pickers, settings lock timeout/failure and retry, draft retention, localization/theme application,
  680 x 640 layout, one top-level window and accessible names for 13 focusable settings controls.
- 28 native screenshots were generated under `build/native-evidence/`; representative light text-result and dark
  Chinese settings views were visually inspected. The measured desktop was 168 DPI (175%) with High Contrast off.
- Final process check found zero `AegisVault` and zero `AegisVault.Backend` processes.

The locally accepted candidate artifacts are not release provenance. `AegisVault.exe` and the backend carry `2.3.0.0`; product/display metadata is
`2.3`. The generated names are `AegisVault-v2.3-win64.zip`, `AegisVault-v2.3.cdx.json` and `SHA256SUMS`. Optional
signing reported `unsigned-optional` because no certificate was configured.

## Remaining gates and risks

- The new 15-second request-timeout and cleanup-failure messages were verified in both locale resources and
  linked ViewModel/service behavior, but were not displayed through a fault-injected packaged native UI.
- Manual Narrator, real High Contrast, 100/125/150/200% DPI, multi-monitor transitions and manual window-close
  timing were not run. The native harness covered one 175% DPI desktop and automated close/cancel behavior.
- Required-signing and clean-commit reproducibility were not covered by local acceptance. PR review, remote CI,
  annotated tag, provenance and public Release state must be verified from GitHub rather than inferred here.
- Windows tree termination is bounded and scoped to the process created for one request. If the OS refuses
  termination or reaping, the client returns `ipc.cleanup_failed`; it cannot promise cleanup after an OS crash or
  against a deliberately escaping hostile descendant. The packaged backend is local and trusted by the product
  model; numeric tests explicitly use a fault backend and are not evidence that the normal Python backend emits
  malformed values.
