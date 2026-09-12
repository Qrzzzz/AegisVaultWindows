# Release Checklist

Target version: `2.8`.

The authoritative release constants are in `src/aegisvault/version.py`. Artifact names are derived only after those constants and `pyproject.toml` pass `scripts/release_metadata.py`; workflows must not embed a versioned asset name.

## Repository Gates

- Protect the default branch, `master`, and require the `Quality` source/package jobs plus the relevant `Security` jobs.
- Enable the dependency graph and Dependency Review. Enable GitHub Code Security/CodeQL where the repository visibility and plan require an explicit setting.
- Create a GitHub Environment named `release`. Required reviewers are recommended so the publish job cannot proceed only because a tag was pushed.
- Allow GitHub Actions to create artifact attestations and Releases. The release jobs declare only `contents`, `id-token` and `attestations` permissions needed by their stage.
- Keep Actions from forks untrusted. Quality and Security pull-request jobs receive no signing or publication secrets.
- Set repository variable `AEGISVAULT_SIGNING_MODE` to `Optional` or `Required`. Production repositories should use `Required` once signing is provisioned.
- For real signing, set secrets `AEGISVAULT_SIGNING_CERTIFICATE_BASE64` and `AEGISVAULT_SIGNING_CERTIFICATE_PASSWORD`. Optionally set `AEGISVAULT_TIMESTAMP_URL`. Never commit a PFX, password or synthetic certificate.

## Dependency Locks

Regenerate both locks from `pyproject.toml` with a reviewed `uv` version, then inspect the dependency diff:

```powershell
uv pip compile pyproject.toml --python-version 3.11 --universal --generate-hashes --no-header --no-annotate --output-file requirements.lock
uv pip compile pyproject.toml --extra dev --python-version 3.11 --universal --generate-hashes --no-header --no-annotate --output-file requirements-dev.lock
```

CI installs `requirements-dev.lock` with `--require-hashes` and binary distributions only. The CycloneDX SBOM is generated from the runtime `requirements.lock`.

## Candidate Verification

- Confirm `pyproject.toml`, `src/aegisvault/version.py`, README, SECURITY, CHANGELOG, QA checklist and release notes all reference `2.8` consistently.
- Run `.\scripts\verify_release.ps1 -Build -Zip -InstallDependencies` in a clean Windows checkout.
- Confirm `dist\AegisVault\AegisVault.exe` passes native interaction checks and its backend passes isolated smoke.
- Confirm the PE is AMD64/PE32+ GUI and contains icon, group-icon, manifest and exact `2.8.0.0` version resources.
- Confirm `dist\AegisVault-v2.8-win64.zip` contains the complete self-contained WinUI and backend folder with identical bytes.
- Confirm `dist\AegisVault-v2.8.cdx.json` is CycloneDX JSON 1.6 and binds the source commit plus executable/ZIP digests.
- Confirm `SHA256SUMS` contains exactly the ZIP and SBOM.
- Complete the manual UI and security checks in `docs/QA_CHECKLIST.md`; packaged headless smoke is not a substitute for manual Windows acceptance.

## Tag Binding

- For 2.8, preserve the substantive implementation commit authored by `Codex <codex@openai.com>` when integrating into `master` (prefer a merge that retains the commit). Verify GitHub resolves the commit author to `codex` and includes that account in the native repository Contributors list. A README credit or merge-only attribution does not satisfy this requirement.
- Merge the exact reviewed candidate into `master`.
- Create an annotated two-component tag such as `git tag -a v2.8 <merge-sha> -m "AegisVault v2.8"`.
- The tagged commit must be contained in `origin/master`, the tag must resolve to the workflow event commit, and `RELEASE_TAG` must exactly match the tag.
- Push only after reviewing the tag object and commit. A lightweight tag, prerelease suffix, dirty source or tag/source mismatch fails before packaging.

## GitHub Release

The public asset set is exactly:

- `AegisVault-v2.8-win64.zip`
- `AegisVault-v2.8.cdx.json`
- `SHA256SUMS`

The workflow attests all three files, uploads an internal immutable job artifact, and sends the publish job through the `release` Environment. The publisher creates or resumes a draft, refuses unexpected or byte-mismatched assets, downloads every asset again, verifies SHA-256 and provenance against the tag commit/workflow, and only then clears the draft flag.

If the same tag already has a public Release, the workflow performs the same exact asset, digest and provenance verification and exits successfully without mutation. Any difference fails closed. It never deletes, replaces or uploads with `--clobber` to a public Release.

## Security Triage

- Retain the dependency-review JSON, pip-audit JSON and CodeQL SARIF artifacts from the `Security` workflow.
- Treat advisories as dependency evidence requiring reachability and product-impact analysis, not automatic product-vulnerability declarations.
- Distinguish an advisory finding from a scanner/network/tool failure; both block the gate, but only the former enters vulnerability triage.
