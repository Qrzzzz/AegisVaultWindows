# AegisVault 2.10 acceptance

Baseline: `661bb17fa3236ec00986f1ef5a3a0f0d1046c533`. Scope: Issues #48, #49 and #50.

## Local verification

- Python 3.13.16: 409 tests passed, 82% coverage; Ruff and Mypy passed (28 source files). Deep headers are classified as `crypto.invalid_header`; actual backend queues continue after the failed item.
- Linked-source C# IPC: all 26 scenarios passed, including genuine 2.9 long-password text/file fixtures, Unicode password boundaries, explicit new-encryption rejection and deep-header file isolation.
- Web: 13 unit tests, TypeScript/Vite production build and all 10 existing Playwright browser regressions passed. A further nine CLI-driven browser checks passed for legacy passwords, ASCII/CJK/non-BMP new-encryption boundaries and retained drafts/focus after rejection. Four actual Worker tokens were decrypted by the Python backend.
- Windows x64 Release publish, isolated packaged backend smoke, PyInstaller input-root audit and PE/ZIP/CycloneDX/checksum audit passed with exact 2.10 metadata. This pre-commit local package is acceptance evidence; public assets are rebuilt independently from the annotated release tag.
- Focused native light/English and dark/Chinese runs passed at actual 168 DPI (175%): full 1024/1025/non-BMP/legacy 32769-unit passwords, correction focus, deep-header queue continuation, read-only output policy and preservation of the old backend overwrite preference.
- A final native run also decrypted four tokens produced by the actual browser Worker (ASCII 1025/32768, CJK 32768 and non-BMP 16384 passwords) through the packaged desktop password field and backend. The temporary harness fixture was restored afterwards. Focused checks use `AEGISVAULT_210_ONLY=1`; ordinary runs still execute the full suite.
- The Web lock patches build dependency `source-map-js` to 1.2.2 for GHSA-68fv-2mgg-jv7q. `npm audit` reports zero vulnerabilities.
- Local signing status is `unsigned-optional`. GitHub build provenance and an Authenticode signature are separate checks.

The first full native run hit a picker focus restoration race in the test driver. An isolated queue run passed. A second run read initial window bounds before activation and later restored invalid bounds. The harness now waits for activated window bounds and picker launcher focus, without changing production behavior or extending deadlines. The final full light/English run passed Text/File/Base64, boundary imports, queue keyboard/failure/retry actions, collision numbering, cancellation, settings transactions, language/theme changes, minimum-window visibility, accessible names and clean shutdown.

Logs and screenshots are preserved in the local `AegisVaultBuild/evidence/v2.10` directory.

## Remote publication gates

The PR and merged commit must pass Quality, Security and the actual post-merge Pages deployment. The annotated `v2.10` tag must bind the reviewed source in `origin/master`. The [Release workflow](https://github.com/Qrzzzz/AegisVaultWindows/actions/workflows/release.yml) rebuilds, audits, attests, downloads and verifies the exact ZIP, SBOM and `SHA256SUMS` before clearing the draft flag. These later remote results are recorded by GitHub checks and the release run; local tests do not establish publication success.

## Manual coverage boundaries

Automated UIA interaction and screenshots do not prove actual Narrator speech or the complete physical multi-monitor DPI matrix. Existing manual coverage limits remain recorded separately; they are not counted as passed by source, mock or headless checks.
