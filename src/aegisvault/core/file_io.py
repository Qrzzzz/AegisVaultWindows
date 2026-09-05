"""Low-level filesystem primitives for core crypto workflows."""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from aegisvault.core.exceptions import FileIOError

TEMP_NAME_PREFIX = ".aegisvault-"
TEMP_NAME_SUFFIX = ".tmp"
TEMP_RANDOM_BYTES = 12
TEMP_CREATE_ATTEMPTS = 128


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError as exc:
        raise FileIOError(f"Cannot read file size: {path}", code="file.stat_failed") from exc


def ensure_input_unchanged(source: BinaryIO, initial: os.stat_result, bytes_read: int) -> None:
    """Reject detectable changes to the opened input; this is not a snapshot lock."""

    final = os.fstat(source.fileno())
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if bytes_read != initial.st_size or any(getattr(initial, field) != getattr(final, field) for field in fields):
        raise FileIOError("Input file changed during processing.", code="file.input_changed")


def ensure_output_parent(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileIOError(f"Cannot create output directory: {path.parent}", code="file.mkdir_failed") from exc


def ensure_distinct_paths(input_path: Path, output_path: Path) -> None:
    """Reject an output that aliases the input path, including hard links."""

    source = input_path.expanduser().resolve()
    target = output_path.expanduser().resolve()
    same_file = source == target
    if not same_file and source.exists() and target.exists():
        try:
            same_file = source.samefile(target)
        except OSError:
            same_file = False
    if same_file:
        raise FileIOError("Input and output paths must be different.", code="file.same_input_output")


def _publish_no_overwrite(temp_name: str, final_path: Path) -> bool:
    """Atomically publish without replacing an existing destination.

    Windows rename is no-clobber and also works on filesystems without hard
    links. POSIX rename replaces, so those platforms use atomic link creation.
    The return value reports whether the temporary name was consumed.
    """

    if os.name == "nt":
        os.rename(temp_name, final_path)
        return True
    os.link(temp_name, final_path)
    try:
        os.unlink(temp_name)
    except OSError:
        return False
    return True


def _create_sibling_temp(parent: Path) -> tuple[int, str]:
    """Securely create a fixed-length sibling without disclosing the target name."""

    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    for _attempt in range(TEMP_CREATE_ATTEMPTS):
        name = f"{TEMP_NAME_PREFIX}{secrets.token_hex(TEMP_RANDOM_BYTES)}{TEMP_NAME_SUFFIX}"
        path = os.path.join(parent, name)
        try:
            return os.open(path, flags, 0o600), path
        except FileExistsError:
            continue
    raise FileIOError("Could not create a unique temporary file.", code="file.write_failed")


@contextmanager
def atomic_binary_writer(final_path: Path, *, overwrite: bool = False) -> Iterator[BinaryIO]:
    """Write to a temporary sibling and publish atomically only after success.

    No-overwrite publication uses a platform no-clobber primitive and fails if
    another writer wins the destination name first.
    """

    final_path = final_path.expanduser().resolve()
    ensure_output_parent(final_path)
    if final_path.exists() and not overwrite:
        raise FileIOError(f"Output already exists: {final_path}", code="file.output_exists")

    fd = -1
    temp_name = ""
    try:
        fd, temp_name = _create_sibling_temp(final_path.parent)
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temp_name, final_path)
            temp_name = ""
        else:
            try:
                temp_consumed = _publish_no_overwrite(temp_name, final_path)
            except FileExistsError as exc:
                raise FileIOError(f"Output already exists: {final_path}", code="file.output_exists") from exc
            if temp_consumed:
                temp_name = ""
    except FileIOError:
        raise
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
