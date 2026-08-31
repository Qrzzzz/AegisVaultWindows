"""Generate a reproducible CycloneDX SBOM for the locked runtime closure."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import uuid
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from release_metadata import ROOT, load_release_metadata


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tool_path() -> Path:
    scripts_dir = Path(sys.executable).resolve().parent
    candidate = scripts_dir / ("cyclonedx-py.exe" if os.name == "nt" else "cyclonedx-py")
    if not candidate.is_file():
        raise RuntimeError(f"cyclonedx-py is not installed next to the active interpreter: {candidate}")
    return candidate


def _source_date_epoch() -> int:
    value = subprocess.run(
        ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", "HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()
    return int(value)


def _sort_bom(bom: dict[str, Any]) -> None:
    components = bom.get("components", [])
    components.sort(key=lambda item: (item.get("name", "").casefold(), item.get("version", ""), item.get("bom-ref", "")))
    dependencies = bom.get("dependencies", [])
    for dependency in dependencies:
        dependency["dependsOn"] = sorted(dependency.get("dependsOn", []))
    dependencies.sort(key=lambda item: item.get("ref", ""))


def _active_dependency_names(requirements: list[str] | None) -> set[str]:
    names: set[str] = set()
    for value in requirements or []:
        requirement = Requirement(value)
        if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
            names.add(canonicalize_name(requirement.name))
    return names


def _wire_dependency_graph(bom: dict[str, Any], root_ref: str) -> None:
    components = bom.get("components", [])
    references = {
        canonicalize_name(component["name"]): component["bom-ref"]
        for component in components
        if component.get("name") and component.get("bom-ref")
    }
    dependencies: list[dict[str, Any]] = []
    for name, reference in references.items():
        try:
            requires = importlib.metadata.distribution(name).requires
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(f"Locked SBOM component is not installed: {name}") from exc
        depends_on = sorted(references[item] for item in _active_dependency_names(requires) if item in references)
        dependencies.append({"ref": reference, "dependsOn": depends_on})

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    root_names = _active_dependency_names(pyproject["project"].get("dependencies", []))
    root_dependencies = sorted(references[name] for name in root_names if name in references)
    if len(root_dependencies) != len(root_names):
        missing = sorted(root_names.difference(references))
        raise RuntimeError(f"SBOM is missing direct project dependencies: {missing}")
    dependencies.append({"ref": root_ref, "dependsOn": root_dependencies})
    bom["dependencies"] = dependencies


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-tag")
    parser.add_argument("--source-date-epoch", type=int)
    args = parser.parse_args()

    metadata = load_release_metadata(expected_tag=args.expected_tag)
    requirements = args.requirements.resolve(strict=True)
    executable = args.executable.resolve(strict=True)
    zip_path = args.zip.resolve(strict=True)
    output = args.output.resolve()
    epoch = args.source_date_epoch if args.source_date_epoch is not None else _source_date_epoch()
    timestamp = dt.datetime.fromtimestamp(epoch, tz=dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aegisvault-sbom-") as temporary_dir:
        raw_output = Path(temporary_dir) / "raw.cdx.json"
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PYTHONWARNINGS"] = "ignore:The Component this BOM is describing"
        subprocess.run(
            [
                str(_tool_path()),
                "requirements",
                str(requirements),
                "--pyproject",
                str(ROOT / "pyproject.toml"),
                "--mc-type",
                "application",
                "--spec-version",
                "1.6",
                "--output-reproducible",
                "--output-format",
                "JSON",
                "--output-file",
                str(raw_output),
                "--validate",
            ],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        bom = json.loads(raw_output.read_text(encoding="utf-8"))

    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise RuntimeError("cyclonedx-py returned an unexpected BOM format")
    serial_seed = f"aegisvault:{metadata['version']}:{_sha256(requirements)}"
    bom["serialNumber"] = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)}"
    bom["version"] = 1
    bom_metadata = bom.setdefault("metadata", {})
    bom_metadata["timestamp"] = timestamp
    component = bom_metadata.setdefault("component", {})
    component["type"] = "application"
    component["name"] = "aegisvault-desktop"
    component["version"] = metadata["version"]
    component["bom-ref"] = f"pkg:pypi/aegisvault-desktop@{metadata['version']}"
    component["purl"] = component["bom-ref"]
    component["hashes"] = [{"alg": "SHA-256", "content": _sha256(executable)}]
    component["properties"] = sorted(
        [
            {"name": "aegisvault:artifact:executable:name", "value": executable.name},
            {"name": "aegisvault:artifact:executable:sha256", "value": _sha256(executable)},
            {"name": "aegisvault:artifact:zip:name", "value": zip_path.name},
            {"name": "aegisvault:artifact:zip:sha256", "value": _sha256(zip_path)},
            {"name": "aegisvault:source:commit", "value": subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()},
        ],
        key=lambda item: item["name"],
    )
    _wire_dependency_graph(bom, component["bom-ref"])
    _sort_bom(bom)
    output.write_text(json.dumps(bom, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
