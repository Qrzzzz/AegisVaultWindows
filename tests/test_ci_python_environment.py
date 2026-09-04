from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _powershell(command: str, environment: dict[str, str]) -> dict[str, object]:
    pwsh = shutil.which("pwsh")
    assert pwsh is not None, "Windows CI environment regression tests require PowerShell 7."
    result = subprocess.run(
        [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", command],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}"
    records = [line.removeprefix("CI_PROBE=") for line in result.stdout.splitlines() if line.startswith("CI_PROBE=")]
    assert len(records) == 1, result.stdout[-4000:]
    return json.loads(records[0])


@pytest.fixture
def workspace() -> Iterator[Path]:
    build_root = ROOT / "build"
    build_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ci-python-resolution-", dir=build_root) as directory:
        path = Path(directory)
        assert path.parent == build_root
        yield path


@pytest.mark.parametrize("first_interpreter", ["setup-python", "venv"])
def test_bootstrap_selects_one_python_and_preserves_priority_across_steps(
    workspace: Path, first_interpreter: str
) -> None:
    assert os.name == "nt", "The Windows bootstrap regression requires a real Windows runner."
    existing_venv = workspace / "existing-venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(existing_venv)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=120,
    )
    base_python = Path(getattr(sys, "_base_executable", sys.executable))
    venv_python = existing_venv / "Scripts" / "python.exe"
    candidates = [base_python, venv_python]
    if first_interpreter == "venv":
        candidates.reverse()
    assert all(path.is_file() for path in candidates)
    assert candidates[0].parent != candidates[1].parent

    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    if first_interpreter == "venv":
        environment["VIRTUAL_ENV"] = str(existing_venv)
    # setup-python and Windows runners can expose several real python.exe files.
    # Include both candidates before the original PATH, without passing -BasePython.
    environment["PATH"] = os.pathsep.join([*(str(path.parent) for path in candidates), environment["PATH"]])
    destination = workspace / "new-venv"
    environment["CI_TEST_ENVIRONMENT"] = str(destination)
    exports = {"GITHUB_ENV": workspace / "github-env", "GITHUB_PATH": workspace / "github-path"}
    for name, path in exports.items():
        path.touch()
        environment[name] = str(path)

    first_step = _powershell(
        r"""
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 is required.' }
$Candidates = @((Get-Command python -CommandType Application -ErrorAction Stop).Source)
. ./scripts/initialize_ci_environment.ps1 -EnvironmentPath $env:CI_TEST_ENVIRONMENT -ExportGitHubEnvironment
$Result = [ordered]@{
    candidates = $Candidates
    base_python = $BasePython
    resolved_python = $ResolvedPython
    virtual_env = $env:VIRTUAL_ENV
}
Write-Output ('CI_PROBE=' + ($Result | ConvertTo-Json -Compress))
""",
        environment,
    )
    assert first_step["candidates"][:2] == [str(path) for path in candidates]
    assert first_step["base_python"] == str(candidates[0])
    new_python = destination / "Scripts" / "python.exe"
    assert first_step["resolved_python"] == str(new_python)
    assert first_step["virtual_env"] == str(destination)
    assert exports["GITHUB_ENV"].read_text(encoding="utf-8").splitlines() == [f"VIRTUAL_ENV={destination}"]
    exported_paths = exports["GITHUB_PATH"].read_text(encoding="utf-8").splitlines()
    assert exported_paths == [str(new_python.parent)]

    # A new process receives only the runner's environment-file exports, not the
    # previous PowerShell process's variables or command-resolution cache.
    next_environment = environment.copy()
    next_environment["VIRTUAL_ENV"] = exports["GITHUB_ENV"].read_text(encoding="utf-8").strip().split("=", 1)[1]
    next_environment["PATH"] = os.pathsep.join([*exported_paths, environment["PATH"]])
    second_step = _powershell(
        r"""
$ErrorActionPreference = 'Stop'
$Commands = @(Get-Command python -ErrorAction Stop)
$Probe = (& python -c "import json, sys; print(json.dumps({'executable': sys.executable, 'prefix': sys.prefix, 'base_prefix': sys.base_prefix}))") -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'The next-step interpreter failed.' }
$Result = [ordered]@{
    command_count = $Commands.Count
    command_source = $Commands[0].Source
    virtual_env = $env:VIRTUAL_ENV
    probe = ($Probe | ConvertFrom-Json)
}
Write-Output ('CI_PROBE=' + ($Result | ConvertTo-Json -Compress))
""",
        next_environment,
    )
    assert second_step["command_count"] == 1
    assert second_step["command_source"] == str(new_python)
    assert second_step["virtual_env"] == str(destination)
    assert second_step["probe"]["executable"] == str(new_python)
    assert second_step["probe"]["prefix"] == str(destination)
    assert second_step["probe"]["prefix"] != second_step["probe"]["base_prefix"]
