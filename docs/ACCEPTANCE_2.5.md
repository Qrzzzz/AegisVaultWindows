# AegisVault 2.5 — acceptance evidence

Status: source, linked IPC and package checks passed; a complete native retry passed, but an earlier
native close crash remains unexplained. Automatic publication is held pending that stability assessment.
No 2.5 publication is established by this document.

Baseline: v2.4 / `afac428887c07c5445d1720b73d8815f84f35474`.
Scope: #9, #10, #11 and #20. Only #20 requires a new production implementation;
the first three already have 2.2 repairs and real-file/process regressions.

The new IPC cases fail against the unmodified 2.4 client with DecoderFallbackException for invalid
line bytes, invalid continuation bytes and truncated UTF-8 at EOF. The valid split non-BMP/CRLF control passes.
Logs are retained in the ignored `build/acceptance-2.5/` directory. The earlier 2.4 independent audit is
retained as text evidence in `build/final-review-2.4/`; downloaded assets and generated binaries were removed.

## Executed checks

- compileall and Ruff passed; mypy passed for 27 source files.
- 323 Python tests passed in the combined run. Two Windows CI bootstrap tests failed in the nested
  launcher with missing captured stdout, then both passed from the direct Python entry point unchanged.
  Coverage was 80.65%. This is not recorded as a single uninterrupted 325-test passing run.
- The 55 cases directly covering #9/#10/#11 passed: 28 Base64 input-consistency cases, 10 settings recovery
  cases and 17 settings transaction cases, including real multi-process serialization and bounded lock waits.
- All 17 linked-source IPC scenarios passed after the fix, including all three previously failing UTF-8
  cases, split non-BMP/CRLF control, no-read/cancellation, terminal-without-exit, history failure, numeric
  errors, response limits, process reaping and real-backend text result reuse.
- x64 Release WinUI/backend build, isolated packaged backend smoke, ZIP/SBOM/checksum generation and
  artifact audit passed. Signing status is `unsigned-optional`, not Authenticode-signed.
- 15 final version/source-format checks and `git diff --check` passed.

## Native gate

The unchanged NativeTests harness ran against the local 2.5 package at DPI 168, light/en-US. It passed
text validation/focus, password clearing, clipboard/save picker, boundary UTF-8 import and AGV1 reuse,
file encryption/decryption, repeated wrapper/restore collisions, cancellation cleanup, Base64 text/file,
long target names, settings lock failures, retained drafts, localization/theme application and accessible
settings names. It then detected application exit code `-1073741819` (`0xC0000005`) during close.
The stderr stack points to `Marshal.Release` / `ComWrappers.NativeObjectWrapper.Finalize`.
The harness subsequently also failed while trying to capture the already-closed window. This secondary
capture error does not erase the application exit failure and is not counted as the product root cause.

The official v2.4 ZIP was then downloaded as a diagnostic baseline and verified against SHA-256
`e4489d3a6c5f9ec75643d8fdee75290609731f6ac2482afd6b4815bcdc961c0d`. It passed the complete same native
suite with exit 0. A subsequent full run of the local v2.5 package also passed every scenario including
ContentDialog close, cooperative shutdown and exit 0. The .NET, WinUI and WinRT runtime versions match
between the two packages; the v2.5 changes do not upgrade them. One failed and one successful candidate
run are insufficient to establish the cause or prove the intermittent exit failure is resolved.

Full dark-mode, High Contrast, Narrator and multi-monitor/DPI acceptance is not established by this run.
No UI or COM lifecycle changes are included in the four-issue scope. The anomaly is retained as a release
assessment item; it is not promoted to a confirmed regression caused by #20's decoding change.

## Evidence and binding

Logs: `build/acceptance-2.5/{ipc-red,ipc-green,verify-build,ci-bootstrap-retry,build,native,metadata-final}.log`
and their error/exit sidecars. Native screenshots are under `build/acceptance-2.5/native/`.
Comparison and retry logs are `native-baseline.*` and `native-retry.*`, with screenshots in the matching
directories and runtime versions/hashes in `runtime-comparison.json`. The temporary baseline package
was removed after comparison; logs and screenshots remain.
Python imports and C# linked sources point to this worktree. The build uses the current candidate working
tree; an SBOM source field derived from HEAD is not evidence that this uncommitted candidate was released.
Any future release must rebuild from its final exact commit and pass the remote publication checks.
