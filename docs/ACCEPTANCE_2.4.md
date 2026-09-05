# AegisVault 2.4 — local acceptance evidence

Status: **pre-release local acceptance complete**, 2026-09-05. This record does not itself establish a commit,
push, PR, merge, tag, remote CI run, attestation or GitHub Release; publication state must be verified remotely.

## Source and baseline

- The independent worktree started clean at detached `4aa2828430e6a4c09fffd0c46a61e0ce7b78f374`, the v2.3/PR #18
  merge commit. After fetch, `origin/master`, `origin/HEAD` and tag `v2.3` resolved to the same commit.
- The 2.2 Base64/settings transaction repairs and 2.3 IPC lifecycle, cancellation, numeric validation and localized
  errors were present before changes. No reset, commit, push or remote release mutation was performed during this
  local acceptance run.
- Historical 2.1 audit material was used only as a locator. Reproduction scripts were rebuilt in this task's ignored
  `build/aegisvault-2.4-local-evidence/` directory and explicitly imported this worktree's source with Python `-I`.

## Baseline failures reproduced

- #12: 2,097,152 ASCII characters successfully produced 2,796,204-byte Base64 and 2,796,540-byte AGV1 results.
  The same real backend fully reversed both, but `WorkflowViewModel.UseResult()` returned false with
  `resource.limit_exceeded`; both results also exceeded the 2 MiB UTF-8 file-import limit.
- #13: three real Base64 and AGV1 wraps produced `report.txt.{b64,agv}`, `report.txt (1).{b64,agv}` and
  `report.txt (2).{b64,agv}`. Restoring the numbered wrappers returned `report.txt (1)` / `report.txt (2)` with
  suffixes `.txt (1)` / `.txt (2)`, though content bytes remained correct.
- #14: source components of 237 and 238 characters produced otherwise writable target components of 241 and 242.
  The old target-derived temp components were 255 and 256 characters: the first succeeded and the second returned
  `file.write_failed`. The source remained intact and no temp residue remained.

## Candidate design

- `src/aegisvault/text_limits.json` is the single packaged budget source. Both runtimes validate it, `hello` echoes
  it and WinUI rejects a backend mismatch. The conservative plaintext budget accounts for UTF-8, UTF-16, JSON
  escaping, Base64, maximum AGV1 header/framing/tag overhead and the 16 MiB transport boundary.
- Wrapper collision numbering operates on the logical original name before appending `.agv` or `.b64`; restoration
  continues to strip only the known wrapper suffix. Atomic no-clobber remains the final race authority.
- Temp components are CSPRNG-derived, created with exclusive OS flags, fixed at 40 characters and remain siblings
  of the final target. Windows rename and POSIX link publication paths are unchanged.

## Executed validation

- `scripts/verify_release.ps1 -Build -Zip -SigningMode Optional` passed: compileall, Ruff, mypy, 325 pytest cases
  in 44.17 seconds, 80.65% coverage, the complete linked-source IPC lifecycle harness, an x64 Release WinUI build,
  isolated packaged-backend AGV1/Base64 smoke, source-root audit (358 paths), SBOM, checksums and artifact audit.
- Exact boundary coverage passed for ASCII, BMP and non-BMP input, including full-size Base64 and AGV1 roundtrips,
  `UseResult`, UTF-8 import, over-budget rejection before expensive work and a bounded 16 MiB IPC response line.
- Collision coverage passed for multi-dot, hidden, extensionless, parenthesized and Unicode names, three consecutive
  Base64/AGV wrappers and real concurrent no-overwrite publication. Restores preserved suffixes and content bytes.
- Atomic-write coverage passed for the legal 255-character component, CSPRNG collision retry, fixed/non-disclosing
  40-character temp names, illegal final components and cleanup after failure/cancellation.
- Packaged native WinUI automation passed twice: light/en-US and dark/zh-CN at actual DPI 168 with High Contrast
  disabled. It exercised text correction and focus, the UTF-8/AGV1/UseResult boundary, localized over-limit handling,
  Windows App SDK pickers, file/Base64 roundtrips, collision restoration, the legal 242-character target, cooperative
  cancellation, settings transactions, retained drafts, 680 x 640 layout, 13 named focusable settings controls,
  exactly one top-level window, the close dialog and clean process shutdown. Representative screenshots were
  visually inspected for clipping, localization and theme regressions.
- Process counts for `AegisVault`, `AegisVault.Backend` and `AegisVault.NativeTests` were zero before the second run
  and after both runs. A supplemental Codex desktop CUA check was attempted, but this host did not expose a native
  application API; the packaged executable was therefore accepted through the repository's native UI harness and
  captured screenshots.
- `pip check`, `pip-audit` and the transitive NuGet vulnerability audit passed with no reported vulnerable dependency.
- Local candidate artifacts are `AegisVault-v2.4-win64.zip` (99,107,988 bytes),
  `AegisVault-v2.4.cdx.json` (53,702 bytes) and `SHA256SUMS`. The app PE reports file version `2.4.0.0` and product
  version `2.4`; the packaged backend PE reports `2.4.0.0`.

## Pending gates

- Manual Narrator, real High Contrast, the remaining DPI set and required Authenticode signing were not executed and
  cannot be inferred from local automation. PR review, remote CI, tag binding, attestations and public Release are
  separate publication evidence and are intentionally outside this pre-release local record.
