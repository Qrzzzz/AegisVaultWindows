"""Bounded process-shared locks for short settings transactions."""

from __future__ import annotations

import errno
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from aegisvault.core.exceptions import FileIOError, OperationCancelled
from aegisvault.core.models import CancelToken

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

SETTINGS_LOCK_TIMEOUT = 5.0


def check_cancel(token: CancelToken | None) -> None:
    if token and token.cancelled:
        raise OperationCancelled()


def _try_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if sys.platform == "win32":
        # Windows permits locking past EOF; the persistent sidecar can stay empty.
        # LK_NBLCK never invokes the CRT's implicit ten-second retry loop.
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


@contextmanager
def settings_lock(path: Path, timeout: float, token: CancelToken | None) -> Iterator[None]:
    """Closing the handle (also on process exit) releases the OS lock.

    Never unlink the sidecar: a replacement inode would let two writers lock
    different files. It is only a lock identity, not an indication of ownership.
    """

    check_cancel(token)
    deadline = time.monotonic() + timeout
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
    except OSError as exc:
        raise FileIOError("Cannot open settings lock.", code="settings.lock_failed") from exc
    with handle:
        while True:
            check_cancel(token)
            try:
                _try_lock(handle)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise FileIOError("Cannot acquire settings lock.", code="settings.lock_failed") from exc
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FileIOError("Settings are busy; retry the change.", code="settings.lock_timeout") from exc
                time.sleep(min(0.05, remaining))
        check_cancel(token)
        yield
