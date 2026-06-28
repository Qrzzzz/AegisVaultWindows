"""Filesystem helpers and overwrite-safe output path generation."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from aegisvault.core.exceptions import FileIOError


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise FileIOError(f"Cannot read file size: {path}", code="file.stat_failed") from exc


def ensure_input_file(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if not candidate.is_file():
        raise FileIOError(f"Input file does not exist: {candidate}", code="file.not_found")
    return candidate


def ensure_output_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileIOError(f"Cannot create output directory: {path.parent}", code="file.mkdir_failed") from exc


def unique_path(path: Path) -> Path:
    """Return ``path`` or a numbered sibling that does not exist."""

    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10_000):
        candidate = parent / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
    raise FileIOError("Could not find a free output path.", code="file.no_unique_path")


def encrypted_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    candidate = base_dir / f"{input_path.name}.agv"
    return candidate if overwrite else unique_path(candidate)


def base64_encoded_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    candidate = base_dir / f"{input_path.name}.b64"
    return candidate if overwrite else unique_path(candidate)


def base64_decoded_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    name = input_path.name
    if name.lower().endswith(".b64"):
        candidate_name = name.rsplit(".", 1)[0]
    else:
        candidate_name = f"{input_path.stem}.base64-decoded{input_path.suffix}"
    candidate = base_dir / candidate_name
    return candidate if overwrite else unique_path(candidate)


def decrypted_output_path(input_path: Path, output_dir: Path | None = None, *, overwrite: bool = False) -> Path:
    base_dir = output_dir or input_path.parent
    name = input_path.name
    lower_name = name.lower()
    if lower_name.endswith(".agv") or lower_name.endswith(".aes") or lower_name.endswith(".b64"):
        candidate_name = name.rsplit(".", 1)[0]
    else:
        candidate_name = f"{input_path.stem}.decrypted{input_path.suffix}"
    candidate = base_dir / candidate_name
    return candidate if overwrite else unique_path(candidate)


@contextmanager
def atomic_binary_writer(final_path: Path, *, overwrite: bool = False) -> Iterator[BinaryIO]:
    """Write to a temporary file and atomically move it into place on success."""

    final_path = final_path.expanduser().resolve()
    ensure_output_parent(final_path)
    if final_path.exists() and not overwrite:
        raise FileIOError(f"Output already exists: {final_path}", code="file.output_exists")

    fd = -1
    temp_name = ""
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{final_path.name}.", suffix=".tmp", dir=str(final_path.parent))
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            yield handle
        if final_path.exists() and not overwrite:
            raise FileIOError(f"Output already exists: {final_path}", code="file.output_exists")
        os.replace(temp_name, final_path)
    except OSError as exc:
        raise FileIOError(f"Could not write output file: {final_path}", code="file.write_failed") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temp_name:
            try:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
            except OSError:
                pass


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
