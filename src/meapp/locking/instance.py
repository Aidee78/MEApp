"""Cross-platform single-instance lock for MEApp."""

from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType

from meapp.exceptions import InstanceAlreadyRunningError


class InstanceLock:
    """Hold an operating-system file lock for this process's lifetime.

    The lock file itself may remain on disk. The OS lock is released when the
    file handle closes or the process terminates, including abnormal exits.
    """

    def __init__(self, lock_file: Path) -> None:
        self.lock_file = Path(lock_file)
        self._handle = None

    def acquire(self) -> None:
        """Acquire the lock without waiting if another process owns it."""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_file.open("a+b")

        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            handle.close()
            raise InstanceAlreadyRunningError(
                "Another MEApp instance is already running."
            ) from exc

        self._handle = handle

    def release(self) -> None:
        """Release the lock and close its handle."""
        if self._handle is None:
            return

        handle, self._handle = self._handle, None
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def __enter__(self) -> InstanceLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.release()
        return False
