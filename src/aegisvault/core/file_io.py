"""Low-level filesystem primitives for core crypto workflows."""

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


def ensure_output_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileIOError(f"Cannot create output directory: {path.parent}", code="file.mkdir_failed") from exc


@contextmanager
def atomic_binary_writer(final_path: Path, *, overwrite: bool = False) -> Iterator[BinaryIO]:
    """Write to a temporary sibling and replace the final path only after success."""

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
