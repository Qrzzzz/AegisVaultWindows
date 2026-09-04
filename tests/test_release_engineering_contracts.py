from __future__ import annotations

import hashlib
import importlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from aegisvault.version import RELEASE_TAG

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
FULL_SHA_ACTION = re.compile(r"^[^/\s]+/[^@\s]+@[0-9a-f]{40}$")


def _workflow(name: str) -> dict[str, Any]:
    value = yaml.load((WORKFLOWS / name).read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(value, dict)
    return value


def _uses(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "uses" and isinstance(item, str):
                found.append(item)
            found.extend(_uses(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_uses(item))
    return found


def _run_script(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *arguments],
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )


def test_all_external_actions_are_pinned_to_full_commits() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = _workflow(path.name)
        actions = _uses(workflow)
        assert actions, f"{path.name} has no actions"
        for action in actions:
            assert FULL_SHA_ACTION.fullmatch(action), f"Unpinned action in {path.name}: {action}"


def test_quality_workflow_has_bounded_least_privilege_jobs() -> None:
    workflow = _workflow("ci.yml")
    assert workflow["permissions"] == {}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    jobs = workflow["jobs"]
    assert set(jobs) == {"source-quality", "windows-package"}
    for job in jobs.values():
        assert int(job["timeout-minutes"]) <= 60
        assert job["permissions"] == {"contents": "read"}


def test_security_workflow_keeps_reports_and_has_manual_schedule() -> None:
    workflow = _workflow("security.yml")
    triggers = workflow["on"]
    assert "schedule" in triggers
    assert "workflow_dispatch" in triggers
    assert set(workflow["jobs"]) == {"dependency-review", "pip-audit", "codeql"}
    text = (WORKFLOWS / "security.yml").read_text(encoding="utf-8")
    assert "security-reports/dependency-review.json" in text
    assert "security-reports/pip-audit.json" in text
    assert "security-reports/codeql" in text
    assert "do not label it a product vulnerability without analysis" in text


def test_release_workflow_is_tag_only_and_derives_asset_names() -> None:
    workflow = _workflow("release.yml")
    assert set(workflow["on"]) == {"push"}
    assert workflow["permissions"] == {}
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    jobs = workflow["jobs"]
    assert jobs["build-and-attest"]["permissions"] == {
        "attestations": "write",
        "contents": "read",
        "id-token": "write",
    }
    assert jobs["publish"]["permissions"] == {"attestations": "read", "contents": "write"}
    assert jobs["publish"]["environment"] == "release"
    text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    assert "AegisVault-v1.0.0-win64.zip" not in text
    assert "outputs.zip_name" in text
    assert "actions/attest-build-provenance@" in text
    assert "--require-clean" in text


def test_secrets_are_only_referenced_by_tag_release_workflow() -> None:
    assert "secrets." not in (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "secrets." not in (WORKFLOWS / "security.yml").read_text(encoding="utf-8")
    release_text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    assert "secrets.AEGISVAULT_SIGNING_CERTIFICATE_BASE64" in release_text
    assert "New-SelfSignedCertificate" not in (ROOT / "scripts" / "sign_windows_artifact.ps1").read_text(encoding="utf-8")


def test_dependency_locks_are_exact_and_hashed() -> None:
    for relative in ("requirements.lock", "requirements-dev.lock"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "--hash=sha256:" in text
        requirement_lines = [line for line in text.splitlines() if line and not line.startswith((" ", "#", "-"))]
        assert requirement_lines
        assert all("==" in line for line in requirement_lines)
        assert all(">=" not in line and "~=" not in line for line in requirement_lines)
    dev_lock = (ROOT / "requirements-dev.lock").read_text(encoding="utf-8").casefold()
    for package in ("cyclonedx-bom==", "mypy==", "pefile==", "pip-audit==", "pyinstaller==", "pytest==", "ruff=="):
        assert package in dev_lock
    assert "pyside6" not in dev_lock
    assert "PySide6" not in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_release_metadata_cli_derives_current_public_assets() -> None:
    result = _run_script("release_metadata.py", "--expected-tag", RELEASE_TAG)
    assert result.returncode == 0, result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["zip_name"] == f"AegisVault-{RELEASE_TAG}-win64.zip"
    assert metadata["public_assets"] == [metadata["zip_name"], metadata["sbom_name"], "SHA256SUMS"]
    wrong = _run_script("release_metadata.py", "--expected-tag", "v9.9.9")
    assert wrong.returncode != 0


def test_checksum_generator_is_sorted_and_exact(tmp_path: Path) -> None:
    second = tmp_path / "b.bin"
    first = tmp_path / "a.bin"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")
    output = tmp_path / "SHA256SUMS"
    result = _run_script("generate_checksums.py", "--output", str(output), str(second), str(first))
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="ascii").splitlines() == [
        f"{hashlib.sha256(b'alpha').hexdigest()}  a.bin",
        f"{hashlib.sha256(b'beta').hexdigest()}  b.bin",
    ]


def test_zip_packager_is_byte_reproducible(tmp_path: Path) -> None:
    executable = tmp_path / "AegisVault.exe"
    executable.write_bytes(b"MZ" + b"deterministic-fixture" * 100)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    epoch = "1700000000"
    for output in (first, second):
        result = _run_script(
            "package_windows.py",
            "--executable",
            str(executable),
            "--output",
            str(output),
            "--source-date-epoch",
            epoch,
        )
        assert result.returncode == 0, result.stderr
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == ["AegisVault.exe"]
        assert archive.read("AegisVault.exe") == executable.read_bytes()


def test_public_release_publisher_has_fail_closed_no_clobber_contract() -> None:
    text = (ROOT / "scripts" / "publish_github_release.py").read_text(encoding="utf-8")
    assert "published-idempotent" in text
    assert "Draft Release contains unexpected assets" in text
    assert '"--signer-digest"' in text
    assert '"--source-digest"' in text
    assert "--clobber" not in text
    build_text = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "audit_build_inputs.py" in build_text
    assert '$env:PYTHONHASHSEED = "0"' in build_text
    assert "$env:PYTHONHASHSEED = $PreviousPythonHashSeed" in build_text
    smoke_text = (ROOT / "scripts" / "smoke_backend.py").read_text(encoding="utf-8")
    assert '"PATH": os.path.join(os.environ["SYSTEMROOT"], "System32")' in smoke_text
    assert "cwd=directory" in smoke_text


def test_locked_installer_checks_the_real_installed_environment() -> None:
    text = (ROOT / "scripts" / "install_locked_dependencies.ps1").read_text(encoding="utf-8")
    assert '"-m", "pip", "check"' in text


def test_all_five_windows_jobs_initialize_and_route_their_environment() -> None:
    expected = {
        ("ci.yml", "source-quality"),
        ("ci.yml", "windows-package"),
        ("security.yml", "pip-audit"),
        ("release.yml", "build-and-attest"),
        ("release.yml", "publish"),
    }
    found = set()
    for name in ("ci.yml", "security.yml", "release.yml"):
        for job_name, job in _workflow(name)["jobs"].items():
            if job["runs-on"] != "windows-latest":
                continue
            found.add((name, job_name))
            steps = job["steps"]
            setup = next(index for index, step in enumerate(steps) if step.get("uses", "").startswith("actions/setup-python@"))
            bootstraps = [index for index, step in enumerate(steps) if "initialize_ci_environment.ps1" in step.get("run", "")]
            assert bootstraps == [setup + 1]
            bootstrap = bootstraps[0]
            assert "-ExportGitHubEnvironment" in steps[bootstrap]["run"]
            assert all("run" not in step for step in steps[:bootstrap])
            install = next(index for index, step in enumerate(steps) if "install_locked_dependencies.ps1" in step.get("run", ""))
            assert bootstrap < install
    assert found == expected

    helper = (ROOT / "scripts" / "initialize_ci_environment.ps1").read_text(encoding="utf-8")
    for contract in (
        '-m venv $EnvironmentRoot',
        '$env:VIRTUAL_ENV = $EnvironmentRoot',
        '$env:PATH = $ScriptsDirectory',
        'AppendAllText($env:GITHUB_ENV',
        'AppendAllText($env:GITHUB_PATH',
        'Refusing to reuse or replace an existing environment',
        'The python command did not resolve to the new isolated environment',
    ):
        assert contract in helper
    assert "Remove-Item" not in helper


def test_published_release_is_verified_without_remote_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    publisher = importlib.import_module("publish_github_release")
    notes = tmp_path / "notes.md"
    notes.write_text("release notes\n", encoding="utf-8")
    names = ["AegisVault-v1.0.0-win64.zip", "AegisVault-v1.0.0.cdx.json", "SHA256SUMS"]
    assets = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        assets.append(path)
    metadata = {
        "tag": "v1.0.0",
        "release_title": "AegisVault v1.0.0",
        "public_assets": names,
    }
    release = {
        "id": 42,
        "tag_name": metadata["tag"],
        "name": metadata["release_title"],
        "prerelease": False,
        "body": "release notes",
        "draft": False,
    }
    verified: list[dict[str, Any]] = []
    monkeypatch.setattr(publisher, "load_release_metadata", lambda **_: metadata)
    monkeypatch.setattr(publisher, "_verify_remote_tag", lambda *_: None)
    monkeypatch.setattr(publisher, "_release", lambda *_: release)
    monkeypatch.setattr(publisher, "_verify_exact_assets", lambda **kwargs: verified.append(kwargs))
    monkeypatch.setattr(publisher, "_run", lambda *_args, **_kwargs: pytest.fail("published release was mutated"))

    result = publisher.publish(
        repo="owner/repo",
        tag="v1.0.0",
        commit="a" * 40,
        notes_path=notes,
        assets=assets,
        signer_workflow="owner/repo/.github/workflows/release.yml",
    )

    assert result == "published-idempotent"
    assert len(verified) == 1


def test_published_release_with_wrong_asset_set_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    publisher = importlib.import_module("publish_github_release")
    local = {"expected.zip": tmp_path / "expected.zip"}
    local["expected.zip"].write_bytes(b"expected")
    release = {"assets": [{"name": "unexpected.zip", "state": "uploaded", "size": 8}]}
    monkeypatch.setattr(publisher, "_download_and_verify", lambda *_: pytest.fail("unexpected asset downloaded"))
    monkeypatch.setattr(publisher, "_verify_attestation", lambda *_: pytest.fail("unexpected asset attested"))

    with pytest.raises(publisher.PublishError, match="asset set mismatch"):
        publisher._verify_exact_assets(
            repo="owner/repo",
            release=release,
            local_assets=local,
            tag="v1.0.0",
            commit="a" * 40,
            signer_workflow="owner/repo/.github/workflows/release.yml",
        )
