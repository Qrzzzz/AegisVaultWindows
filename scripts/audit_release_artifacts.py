"""Audit the self-contained WinUI folder, backend archive, ZIP, SBOM and hashes."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path

import pefile
from PyInstaller.archive.readers import CArchiveReader
from release_metadata import ROOT, load_release_metadata


class AuditError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def _audit_pe(path: Path, version: str, signing_mode: str, *, gui: bool) -> None:
    with pefile.PE(str(path)) as pe:
        _require(pe.FILE_HEADER.Machine == 0x8664 and pe.OPTIONAL_HEADER.Magic == 0x20B, f"Not x64: {path.name}")
        _require(pe.OPTIONAL_HEADER.Subsystem == (2 if gui else 3), f"Unexpected PE subsystem: {path.name}")
        info = pe.VS_FIXEDFILEINFO[0]
        major, minor = (int(part) for part in version.split("."))
        _require(info.FileVersionMS == (major << 16 | minor) and info.FileVersionLS == 0, "PE version mismatch")
        if signing_mode == "Required":
            security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
            _require(security.Size > 0, f"Missing signature: {path.name}")
            result = subprocess.run(["powershell", "-NoProfile", "-File", str(ROOT / "scripts/verify_signature.ps1"),
                                     "-Executable", str(path)], capture_output=True, check=False)
            _require(result.returncode == 0, f"Invalid Authenticode signature: {path.name}")


def _audit_folder(folder: Path, version: str, signing_mode: str) -> None:
    required = {"AegisVault.exe", "AegisVault.dll", "AegisVault.deps.json", "AegisVault.runtimeconfig.json",
                "Microsoft.UI.Xaml.dll", "AegisVault.pri", "coreclr.dll", "backend/AegisVault.Backend.exe",
                "Assets/zh-CN.json", "Assets/en-US.json"}
    files = {path.relative_to(folder).as_posix(): path for path in folder.rglob("*") if path.is_file()}
    missing = {name for name in required if name.casefold() not in {item.casefold() for item in files}}
    _require(not missing, f"Incomplete WinUI bundle: {sorted(missing)}")
    forbidden = ("pyside", "pyqt", "shiboken", "qt6", "qt5", ".qss")
    _require(not any(any(token in name.casefold() for token in forbidden) for name in files), "Retired frontend in bundle")
    _audit_pe(folder / "AegisVault.exe", version, signing_mode, gui=True)
    backend = folder / "backend/AegisVault.Backend.exe"
    _audit_pe(backend, version, signing_mode, gui=False)
    archive = CArchiveReader(str(backend))
    members = set(archive.toc)
    pyz = archive.open_embedded_archive("PYZ.pyz")
    members.update(pyz.toc)
    _require("aegisvault.backend.server" in members, "Backend protocol entry point missing")
    _require(not any(any(token in name.casefold() for token in forbidden) or name.startswith("aegisvault.ui")
                     for name in members), "Retired frontend in backend archive")


def _audit_zip(path: Path, folder: Path, epoch: int) -> None:
    files = {item.relative_to(folder).as_posix(): item for item in folder.rglob("*") if item.is_file()}
    stamp = dt.datetime.fromtimestamp(epoch, tz=dt.UTC)
    expected_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second // 2 * 2)
    with zipfile.ZipFile(path) as archive:
        _require(len(archive.namelist()) == len(files) and set(archive.namelist()) == set(files), "ZIP file set mismatch")
        for name, source in files.items():
            _require(archive.getinfo(name).date_time == expected_time, f"ZIP timestamp mismatch: {name}")
            with archive.open(name) as stream:
                _require(hashlib.file_digest(stream, "sha256").hexdigest() == _sha256(source), f"ZIP bytes mismatch: {name}")


def _audit_sbom(path: Path, executable: Path, zip_path: Path, version: str) -> None:
    bom = json.loads(path.read_text(encoding="utf-8"))
    _require(bom.get("bomFormat") == "CycloneDX" and bom.get("specVersion") == "1.6", "Invalid SBOM format")
    component = bom["metadata"]["component"]
    _require(component["version"] == version, "SBOM version mismatch")
    properties = {item["name"]: item["value"] for item in component["properties"]}
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    _require(properties["aegisvault:source:commit"] == commit, "SBOM source mismatch")
    _require(properties["aegisvault:artifact:executable:sha256"] == _sha256(executable), "SBOM EXE mismatch")
    _require(properties["aegisvault:artifact:zip:sha256"] == _sha256(zip_path), "SBOM ZIP mismatch")
    names = {item["name"].casefold() for item in bom["components"]}
    _require({"cryptography", "microsoft.windowsappsdk", "microsoft.windowsappsdk.winui"}.issubset(names), "Incomplete mixed-runtime SBOM")
    _require(not any("pyside" in name or "shiboken" in name for name in names), "Retired frontend in SBOM")
    refs = {component["bom-ref"], *(item["bom-ref"] for item in bom["components"])}
    for item in bom["dependencies"]:
        _require(item["ref"] in refs and set(item["dependsOn"]).issubset(refs), "Unknown SBOM reference")


def _audit_checksums(path: Path, expected: list[Path]) -> None:
    lines = path.read_text(encoding="ascii").splitlines()
    _require(all(re.fullmatch(r"[a-f0-9]{64}  [^/\\]+", line) for line in lines), "Malformed checksums")
    _require(sorted(lines) == sorted(f"{_sha256(item)}  {item.name}" for item in expected), "Checksum mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--expected-tag")
    parser.add_argument("--signing-mode", choices=("Optional", "Required"), default="Optional")
    parser.add_argument("--executable-only", action="store_true")
    args = parser.parse_args()
    metadata = load_release_metadata(expected_tag=args.expected_tag)
    folder = args.dist / "AegisVault"
    try:
        _audit_folder(folder, metadata["version"], args.signing_mode)
        if not args.executable_only:
            archive = args.dist / metadata["zip_name"]
            sbom = args.dist / metadata["sbom_name"]
            epoch = int(subprocess.check_output(["git", "-C", str(ROOT), "show", "-s", "--format=%ct", "HEAD"], text=True))
            _audit_zip(archive, folder, epoch)
            _audit_sbom(sbom, folder / metadata["exe_name"], archive, metadata["version"])
            _audit_checksums(args.dist / "SHA256SUMS", [archive, sbom])
    except (AuditError, OSError, KeyError, ValueError, pefile.PEFormatError) as exc:
        parser.error(str(exc))
    print(f"WinUI/backend artifact audit passed: {metadata['tag']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
