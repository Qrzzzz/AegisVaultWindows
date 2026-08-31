# Release Engineering Contract

This document describes the automation boundary. It does not change AegisVault UI behavior, cryptographic formats or compatibility policy.

## Trust Flow

1. `src/aegisvault/version.py` supplies the package, display and tag versions.
2. `scripts/release_metadata.py` requires strict `X.Y.Z` / `vX.Y.Z`, checks `pyproject.toml` and release notes, and derives every artifact name.
3. The `Quality` workflow installs the hashed lock, runs compile/Ruff/mypy/pytest with coverage and Qt offscreen smoke, then performs a clean Windows package, packaged smoke and PE/ZIP/SBOM audit.
4. The `Security` workflow performs pull-request dependency review, locked-runtime pip-audit and Python CodeQL. JSON/SARIF reports are retained for triage.
5. A tag Release requires an annotated tag whose commit equals the event commit and is contained in the remote default branch.
6. The same Windows build script produces the executable, deterministic ZIP, reproducible CycloneDX 1.6 SBOM and `SHA256SUMS`.
7. GitHub artifact provenance is issued for the three public assets before the publish job starts.
8. The publish job re-audits the downloaded build output, creates or resumes a draft, byte-verifies its exact asset set, verifies attestations against the tag source digest and signer workflow, then publishes.

## Reproducibility Boundary

Dependencies and build tools are exact and hash locked; GitHub Actions are pinned to full commits; the ZIP timestamp comes from the Git commit; the SBOM removes random/time-dependent values and binds source/artifact hashes. PySide6 is held at the clean-package baseline `6.9.3`; later tested wheels introduced an undeclared host ICU dependency on Windows. Upgrades require a fresh clean-runner PE-import and packaged-smoke audit rather than an unreviewed lock refresh. These controls make the build procedure repeatable and evidence comparable. PyInstaller and Windows signing can still encode toolchain or timestamp-service data, so the contract does not claim independently reproduced executables are necessarily byte-for-byte identical. The release records the actual signed executable and ZIP digests.

## Code Signing Gate

`Optional` means an absent certificate is reported clearly and an unsigned candidate may continue. If certificate secrets are present, signing and local Authenticode validation must succeed even in Optional mode. `Required` means missing secrets, missing SignTool, timestamp failure or invalid Authenticode stops before ZIP/SBOM/checksum creation. The repository never generates or substitutes a test certificate.

## Immutability

Draft Releases are recoverable staging state. Existing draft assets are reused only when bytes match; missing expected assets may be uploaded; unexpected or mismatched assets stop the run. Published Releases are immutable under this workflow. A matching published Release is idempotent success only after exact remote download, digest and provenance verification.
