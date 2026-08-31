"""Audit the Windows PE, ZIP, SBOM and checksums as one release bundle."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import pefile
from PyInstaller.archive.readers import CArchiveReader
from release_metadata import ROOT, load_release_metadata


class AuditError(RuntimeError):
    """Raised when an artifact violates the release contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decode(value: bytes | str) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def _version_strings(pe: pefile.PE) -> dict[str, str]:
    strings: dict[str, str] = {}
    for group in getattr(pe, "FileInfo", []) or []:
        entries = group if isinstance(group, list) else [group]
        for entry in entries:
            if _decode(getattr(entry, "Key", "")) != "StringFileInfo":
                continue
            for table in getattr(entry, "StringTable", []) or []:
                for key, value in table.entries.items():
                    strings[_decode(key)] = _decode(value)
    return strings


def _audit_pe(path: Path, version: str, signing_mode: str) -> None:
    if path.stat().st_size < 1024 * 1024:
        raise AuditError(f"Packaged executable is implausibly small: {path.stat().st_size} bytes")
    pe = pefile.PE(str(path), fast_load=False)
    try:
        if pe.FILE_HEADER.Machine != pefile.MACHINE_TYPE["IMAGE_FILE_MACHINE_AMD64"]:
            raise AuditError(f"Executable is not AMD64 PE: machine=0x{pe.FILE_HEADER.Machine:04x}")
        if pe.OPTIONAL_HEADER.Magic != 0x20B:
            raise AuditError("Executable is not PE32+ (64-bit)")
        if pe.OPTIONAL_HEADER.Subsystem != pefile.SUBSYSTEM_TYPE["IMAGE_SUBSYSTEM_WINDOWS_GUI"]:
            raise AuditError("Executable is not a Windows GUI subsystem image")
        resource_ids = {entry.id for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}
        required_resources = {3, 14, 16, 24}  # icon, group icon, version, manifest
        missing_resources = sorted(required_resources.difference(resource_ids))
        if missing_resources:
            raise AuditError(f"Executable is missing required PE resources: {missing_resources}")
        strings = _version_strings(pe)
        expected_strings = {
            "InternalName": "AegisVault",
            "OriginalFilename": "AegisVault.exe",
            "ProductName": "AegisVault",
            "FileVersion": f"{version}.0",
            "ProductVersion": f"{version}.0",
        }
        for key, expected in expected_strings.items():
            if strings.get(key) != expected:
                raise AuditError(f"PE version resource {key} mismatch: {strings.get(key)!r} != {expected!r}")
        security_directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]]
        if signing_mode == "Required" and (security_directory.VirtualAddress == 0 or security_directory.Size == 0):
            raise AuditError("SigningMode=Required but the PE has no Authenticode certificate table")
    finally:
        pe.close()


def _audit_pyinstaller_archive(path: Path) -> None:
    archive = CArchiveReader(str(path))
    members = {name.replace("\\", "/").casefold() for name in archive.toc}
    required = {
        "pyside6/qt6core.dll",
        "pyside6/qt6gui.dll",
        "pyside6/qt6widgets.dll",
        "pyside6/plugins/platforms/qoffscreen.dll",
        "pyside6/plugins/platforms/qwindows.dll",
        "aegisvault/i18n/locales/en-us.json",
        "aegisvault/i18n/locales/zh-cn.json",
        "aegisvault/resources/app_icon.ico",
        "aegisvault/resources/qss/dark.qss",
        "aegisvault/resources/qss/light.qss",
    }
    missing = sorted(required.difference(members))
    if missing:
        raise AuditError(f"PyInstaller archive is missing runtime resources: {missing}")
    if any(name.startswith("tests/") for name in members):
        raise AuditError("PyInstaller archive unexpectedly contains the test suite")


def _audit_zip(zip_path: Path, executable: Path, source_epoch: int) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if [member.filename for member in members] != [executable.name]:
            raise AuditError(f"ZIP must contain exactly {executable.name}; got {[member.filename for member in members]}")
        member = members[0]
        expected_time = dt.datetime.fromtimestamp(source_epoch, tz=dt.UTC).replace(tzinfo=None)
        expected_tuple = (
            expected_time.year,
            expected_time.month,
            expected_time.day,
            expected_time.hour,
            expected_time.minute,
            expected_time.second // 2 * 2,
        )
        if member.date_time != expected_tuple:
            raise AuditError(f"ZIP timestamp is not SOURCE_DATE_EPOCH: {member.date_time} != {expected_tuple}")
        digest = hashlib.sha256()
        with archive.open(member) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != _sha256(executable):
            raise AuditError("ZIP executable bytes differ from the audited executable")


def _properties(component: dict[str, Any]) -> dict[str, str]:
    return {item["name"]: item["value"] for item in component.get("properties", [])}


def _audit_sbom(sbom_path: Path, executable: Path, zip_path: Path, version: str, commit: str) -> None:
    bom = json.loads(sbom_path.read_text(encoding="utf-8"))
    if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
        raise AuditError("SBOM must be CycloneDX JSON 1.6")
    if not re.fullmatch(r"urn:uuid:[0-9a-f-]{36}", bom.get("serialNumber", "")):
        raise AuditError("SBOM serialNumber must be a deterministic UUID URN")
    component = bom.get("metadata", {}).get("component", {})
    if (component.get("name"), component.get("version"), component.get("type")) != (
        "aegisvault-desktop",
        version,
        "application",
    ):
        raise AuditError("SBOM root component does not match AegisVault source metadata")
    properties = _properties(component)
    expected_properties = {
        "aegisvault:artifact:executable:name": executable.name,
        "aegisvault:artifact:executable:sha256": _sha256(executable),
        "aegisvault:artifact:zip:name": zip_path.name,
        "aegisvault:artifact:zip:sha256": _sha256(zip_path),
        "aegisvault:source:commit": commit,
    }
    for key, expected in expected_properties.items():
        if properties.get(key) != expected:
            raise AuditError(f"SBOM property mismatch for {key}")
    dependency_names = {str(item.get("name", "")).casefold().replace("_", "-") for item in bom.get("components", [])}
    for dependency in ("cryptography", "pyside6"):
        if dependency not in dependency_names:
            raise AuditError(f"SBOM is missing locked runtime dependency: {dependency}")
    component_references = {
        str(item.get("name", "")).casefold().replace("_", "-"): item.get("bom-ref")
        for item in bom.get("components", [])
    }
    graph = {item.get("ref"): set(item.get("dependsOn", [])) for item in bom.get("dependencies", [])}
    root_ref = component.get("bom-ref")
    expected_direct = {component_references["cryptography"], component_references["pyside6"]}
    if graph.get(root_ref) != expected_direct:
        raise AuditError("SBOM root dependency graph does not bind both direct runtime dependencies")
    known_references = {root_ref, *component_references.values()}
    for reference, depends_on in graph.items():
        if reference not in known_references or not depends_on.issubset(known_references):
            raise AuditError("SBOM dependency graph contains an unknown component reference")


def _audit_checksums(path: Path, expected: list[Path]) -> None:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^/\\]+)", line)
        if not match:
            raise AuditError(f"Malformed SHA256SUMS line: {line!r}")
        digest, name = match.groups()
        if name in entries:
            raise AuditError(f"Duplicate checksum entry: {name}")
        entries[name] = digest
    expected_names = {item.name for item in expected}
    if set(entries) != expected_names:
        raise AuditError(f"Checksum asset set mismatch: {sorted(entries)} != {sorted(expected_names)}")
    for item in expected:
        if entries[item.name] != _sha256(item):
            raise AuditError(f"Checksum mismatch: {item.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", required=True, type=Path)
    parser.add_argument("--expected-tag")
    parser.add_argument("--signing-mode", choices=("Optional", "Required"), default="Optional")
    parser.add_argument("--executable-only", action="store_true")
    args = parser.parse_args()
    metadata = load_release_metadata(expected_tag=args.expected_tag)
    dist = args.dist.resolve(strict=True)
    executable = dist / metadata["exe_name"]
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    try:
        _audit_pe(executable, metadata["version"], args.signing_mode)
        _audit_pyinstaller_archive(executable)
        if not args.executable_only:
            zip_path = dist / metadata["zip_name"]
            sbom_path = dist / metadata["sbom_name"]
            checksums_path = dist / metadata["checksums_name"]
            required = [zip_path, sbom_path, checksums_path]
            missing = [str(path) for path in required if not path.is_file()]
            if missing:
                raise AuditError(f"Missing release assets: {missing}")
            allowed_names = {metadata["exe_name"], *metadata["public_assets"]}
            actual_names = {path.name for path in dist.iterdir() if path.is_file()}
            if actual_names != allowed_names:
                raise AuditError(f"Unexpected dist file set: {sorted(actual_names)} != {sorted(allowed_names)}")
            epoch = int(subprocess.run(
                ["git", "-C", str(ROOT), "show", "-s", "--format=%ct", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip())
            commit = subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            _audit_zip(zip_path, executable, epoch)
            _audit_sbom(sbom_path, executable, zip_path, metadata["version"], commit)
            _audit_checksums(checksums_path, [zip_path, sbom_path])
    except (AuditError, json.JSONDecodeError, OSError, pefile.PEFormatError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(f"Release artifact audit passed: {metadata['tag']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
