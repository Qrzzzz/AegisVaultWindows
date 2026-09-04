# Release engineering — 2.1

The authoritative product version is `src/aegisvault/version.py`. Metadata validation checks two-component
`X.Y` / `vX.Y`, Python packaging, WinUI project/assembly versions and matching release notes. Windows binary
metadata uses `X.Y.0.0`. Annotated tag, event SHA and default-branch ancestry checks remain mandatory for release.

The frontend is a self-contained .NET / Windows App SDK x64 folder, built with the SDK in `global.json` and
`packages.lock.json` in locked mode. Python uses hashed `requirements-dev.lock` and `requirements.lock`.
PyInstaller packages only the Core and JSONL backend, with a minimal PATH and an input-root audit. The
application launches the packaged backend by absolute colocated path and sends no secrets on argv.

`build_windows.ps1 -Clean -Zip` validates metadata, packages the backend, builds WinUI Release with warnings
as errors, signs both executables according to SigningMode, and runs isolated backend smoke. It then creates
a deterministic folder ZIP, CycloneDX 1.6 SBOM covering Python, NuGet and implicit .NET runtime packs, and
SHA256SUMS. The audit verifies PE architecture/version, absence of retired UI dependencies in both the
folder and embedded Python archive, required WinUI files, exact ZIP content/digests and SBOM binding.

The unpacked candidate lives at `dist/AegisVault/AegisVault.exe`. The ZIP must include the entire folder
contents, including XAML resources, native runtime DLLs, Assets and backend. A standalone EXE cannot run it.
The public asset set remains ZIP, SBOM and SHA256SUMS; the internal CI artifact also retains the full folder.

Optional signing reports an absent certificate; Required signing rejects it. No synthetic certificate is
substituted. Signed executables are hashed only after signing. Rebuilding with identical inputs is designed
to stabilize ZIP ordering/timestamps and SBOM ordering, but deterministic ZIP generation alone does not prove
independent .NET or signed-binary reproducibility.

Quality runs Python checks and Windows packaging. Security scans both Python and C# with CodeQL; dependency
review inspects Python and NuGet lock changes. Native interaction tests require an interactive Windows
desktop. Full High Contrast, DPI and Narrator checks remain separate measured acceptance gates.

Release workflow preserves least privilege, exact source binding, provenance before publication, and the
release Environment. Published assets are immutable: the publisher verifies matching existing assets without
mutation and refuses missing, unexpected or mismatching assets. Publication requires maintainer authorization,
accepted native UI validation and passing remote quality/security gates before creating the annotated tag.
