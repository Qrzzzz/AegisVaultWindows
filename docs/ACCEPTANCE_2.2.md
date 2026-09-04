# AegisVault 2.2 — acceptance evidence

The following measurements describe the local candidate before publication. Baseline and remote `master` were
`2dd5459b2c97a553041502d0ce1208926dee6383` (2.1), verified on 2026-09-05. The worktree started clean at detached HEAD.
Only issues #9, #10 and #11 are in scope. After reviewing this local acceptance, the maintainer authorized
the 2.2 release and cleanup of this task's intermediate files/worktree on 2026-09-05. Remote evidence is
recorded by the [Quality](https://github.com/Qrzzzz/AegisVaultWindows/actions/workflows/ci.yml),
[Security](https://github.com/Qrzzzz/AegisVaultWindows/actions/workflows/security.yml) and
[Release](https://github.com/Qrzzzz/AegisVaultWindows/actions/workflows/release.yml) runs for the release commit;
the [v2.2 Release](https://github.com/Qrzzzz/AegisVaultWindows/releases/tag/v2.2) carries the public artifacts.

All reproduction files use synthetic data and isolated settings directories. Python is borrowed from an
existing environment, with the current worktree's `src` explicitly selected; no real user configuration
is read or written. Baseline module origins are in `build/acceptance-2.2/baseline-results.jsonl`.

| Issue | Rebuilt baseline failure | Verified candidate result |
| --- | --- | --- |
| #9 | Real second-handle truncation after the first chunk publishes incomplete encoding/decoding and reports success | Both directions raise `file.input_changed`, retain no incomplete output or temporary file; static roundtrip and cancellation controls pass |
| #10 | A 5,000-digit JSON integer makes settings get/update and Base64 return `file.io_error`; ordinary malformed JSON recovers | Real backend subprocesses recover for all three operations and remain usable after saving; valid settings remain compatible |
| #11 | After privacy-off saves false, another process's old recent-add snapshot restores true and one history entry | Lock covers load through save; the waiting process loads the completed preceding transaction and cannot undo privacy-off implicitly |

The new concurrency schedule pauses the first process after load while it owns the lock, observes actual
OS lock contention in the second process, then releases the first. It never waits for two locked loads
simultaneously. Tests also cover both privacy orderings, unrelated field updates, clear/update, timeout,
failed writes, cancelled waits, exceptions and killed owners.

## Local validation results

- Original reproductions: passed all failure-demonstrating assertions; both subprocesses exited zero.
- First targeted candidate run: 52 passed on Windows / Python 3.13.14.
- Final source regression: **301 passed**, including 55 new targeted cases; coverage **79.85%** (70% gate), one full run, 36.02 seconds.
- Compileall, Ruff, Mypy (26 source files), version/metadata and source-format checks: passed.
- Replay of the original three issues with corrected assertions: passed. Configuration recovery additionally passed all nine combinations of bad integer / malformed JSON / valid JSON and get / update / Base64 against the packaged backend, with minimal PATH and isolated profiles.
- WinUI x64 Release publish: passed with warnings as errors and locked NuGet restore, .NET SDK 10.0.400. UI, backend `hello` and package versions are `2.2`; Windows file versions are `2.2.0.0`. The existing backend resource generator also uses four components for its PE ProductVersion string.
- Package smoke (AGV1 text/file and Base64), PyInstaller input-root audit, complete ZIP/SBOM/checksum and binary artifact audit: passed. Signing status: unsigned-optional, no certificate configured.
- Native WinUI interaction: passed in light/en-US and dark/zh-CN on the actual packaged frontend and backend. Both runs exercised localized transaction timeout and lock-open failures, unchanged persisted bytes, retained draft, successful retry, AGV1/Base64 roundtrips, file picker, cancellation/close cleanup, 680 x 640 window and one top-level window.
- Screenshots: 14 per native run, 28 total. Timeout screens visually inspected in both languages; version `2.2`, error, draft state and Save/Discard are visible.
- Actual native DPI: 168 (175%); High Contrast was false. Other DPI/monitor combinations, real High Contrast and Narrator: not run for 2.2.
- Python 3.11/3.12 and POSIX lock fallback: not run locally. The remote Quality workflow covers Python 3.11, 3.12 and 3.13 on Windows.
- Remote CI, clean commit/tag binding, signing and attestations are separate release gates; local test results do not establish their outcomes.
- Final process check: no test Python/backend/frontend/harness processes associated with this worktree remain. Test filesystem: Windows NTFS.

The first PR package run exposed a smoke-harness mismatch: it sent a second request in the same process
immediately after a terminal event, while the real client uses a new process per operation. A deterministic
regression held the real backend worker briefly after its terminal event and reproduced `ipc.busy`.
The smoke now starts one process per call and awaits its exit, retaining deadlines and process-tree
cleanup. This release-tooling correction does not change the backend IPC lifecycle reserved for 2.3.

The measured commands below all exited 0. Set `VIRTUAL_ENV` to the existing Python 3.13.14 environment
or an equivalent hash-locked environment; paths below are normalized for reproduction from this checkout.

```powershell
# From this checkout, with a prepared virtual environment:
$env:VIRTUAL_ENV = (Resolve-Path .venv).Path
$env:PATH = "$env:VIRTUAL_ENV\Scripts;$env:PATH"
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:AEGISVAULT_DOTNET = "$env:LOCALAPPDATA\AegisVaultBuild\dotnet\dotnet.exe"
.\scripts\verify_release.ps1
.\scripts\build_windows.ps1 -Zip -SigningMode Optional
& $env:AEGISVAULT_DOTNET build tests/AegisVault.NativeTests -c Release -warnaserror
.\tests\AegisVault.NativeTests\bin\Release\net10.0-windows\AegisVault.NativeTests.exe dist/AegisVault/AegisVault.exe build/acceptance-2.2/native-light light en-US
.\tests\AegisVault.NativeTests\bin\Release\net10.0-windows\AegisVault.NativeTests.exe dist/AegisVault/AegisVault.exe build/acceptance-2.2/native-dark dark zh-CN
python -I build/acceptance-2.2/verify_candidate.py
```

Logs: `source-final.log`, `package.log`, `native-build.log`, `native-light.log`, `native-dark.log`,
`candidate-results.jsonl` and `candidate-stderr.log`, all under `build/acceptance-2.2/`.
`reproduce_baseline.py` and `baseline-results.jsonl` preserve the original failure-demonstrating run;
the baseline script intentionally expects the old defects and must not be used as a candidate pass criterion.

## Boundaries

Metadata and byte-count checks detect source changes; they do not offer a strict concurrent file snapshot.
Settings locks apply only to cooperating writers and use a persistent empty sidecar. The retry deadline
does not promise to interrupt an operating-system filesystem call stalled by a faulty device or network.
Explicit old WinUI drafts still submit all six preferences and remain last-writer-wins for those fields.
No AGV1 format/algorithm, UI layout, dependency or protocol-version changes are included.
Issues reserved for 2.3 and 2.4 remain outside this work.

The initial local candidate was built from uncommitted work, so its recorded Git SHA was the baseline.
It is not used as the published release artifact. The authorized Release workflow rebuilds from the
reviewed, clean, annotated-tag commit and verifies exact asset bytes and provenance before publication.

Evidence logs and the original baseline reproducer were recorded under `build/acceptance-2.2/` (Git ignored).
These intermediates are removed with the local worktree after publication as requested by the maintainer;
this tracked summary, behavior regressions and remote workflow evidence remain available.
