"""Filesystem helpers and overwrite-safe output path generation."""

from __future__ import annotations

from pathlib import Path

from aegisvault.core.exceptions import FileIOError
from aegisvault.core.file_io import atomic_binary_writer as atomic_binary_writer
from aegisvault.core.file_io import file_size as file_size


def ensure_input_file(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise FileIOError(f"Input file does not exist: {candidate}", code="file.not_found")
    return candidate


def unique_path(path: Path) -> Path:
    """Return ``path`` or a numbered sibling that does not exist."""

    if not path.exists():
        return path
    parent = path.parent
    for index in range(1, 10_000):
        candidate = parent / _numbered_name(path.name, index)
        if not candidate.exists():
            return candidate
    raise FileIOError("Could not find a free output path.", code="file.no_unique_path")


def _numbered_name(name: str, index: int) -> str:
    """Insert a collision number before every logical suffix in ``name``."""

    suffix = "".join(Path(name).suffixes)
    stem = name[:-len(suffix)] if suffix else name
    return f"{stem} ({index}){suffix}"


def _wrapped_output_path(base_dir: Path, logical_name: str, wrapper_suffix: str, *, overwrite: bool) -> Path:
    candidate = base_dir / f"{logical_name}{wrapper_suffix}"
    if overwrite or not candidate.exists():
        return candidate
    for index in range(1, 10_000):
        candidate = base_dir / f"{_numbered_name(logical_name, index)}{wrapper_suffix}"
        if not candidate.exists():
            return candidate
    raise FileIOError("Could not find a free output path.", code="file.no_unique_path")


def encrypted_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    return _wrapped_output_path(base_dir, input_path.name, ".agv", overwrite=overwrite)


def base64_encoded_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    return _wrapped_output_path(base_dir, input_path.name, ".b64", overwrite=overwrite)


def _restored_output_path(base_dir: Path, name: str, *, overwrite: bool) -> Path:
    """Validate the leaf before joining or collision numbering can change its parent."""

    if not name.rstrip(". ") or Path(name).name != name or any(c in name for c in ("/", "\\", "\x00")):
        raise FileIOError("The restored filename is invalid.", code="file.output_name_invalid")
    directory = base_dir.expanduser().resolve()
    candidate = directory / name
    candidate = candidate if overwrite else unique_path(candidate)
    if candidate.resolve().parent != directory or candidate.is_dir():
        raise FileIOError("The restored filename is not a file in the output directory.", code="file.output_name_invalid")
    return candidate


def base64_decoded_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    name = input_path.name
    if name.lower().endswith(".b64"):
        candidate_name = name.rsplit(".", 1)[0]
    else:
        candidate_name = f"{input_path.stem}.base64-decoded{input_path.suffix}"
    return _restored_output_path(base_dir, candidate_name, overwrite=overwrite)


def decrypted_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    name = input_path.name
    lower_name = name.lower()
    if lower_name.endswith(".agv"):
        candidate_name = name.rsplit(".", 1)[0]
    else:
        candidate_name = f"{input_path.stem}.decrypted{input_path.suffix}"
    return _restored_output_path(base_dir, candidate_name, overwrite=overwrite)


def reveal_file(path: Path) -> None:
    """Open the platform file manager and select or show a file."""

    import subprocess
    import sys

    target = path.expanduser().resolve()
    try:
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(target)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent)])
    except OSError as exc:
        raise FileIOError(f"Could not open file manager: {target}", code="file.reveal_failed") from exc
