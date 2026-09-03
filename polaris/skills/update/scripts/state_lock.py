#!/usr/bin/env python3
"""T6 — one writer at a time on a state file, and only its owner may write or release it.

Six panels updating six different lanes lost 7 of 60 updates, each reporting success: every
one read the file before the previous write landed. A lock file fixes that, and then two
subtler things bite:

  * the holder that returns after its lock was stolen must not unlink the thief's lock;
  * and it must not WRITE either — it holds a buffer read before the thief existed, and
    writing it destroys the thief's work under an exit-0 receipt.

So the lock carries `pid:nanos`, the process remembers what it claimed, and `still_mine` is
checked immediately before every write. The wait is longer than the steal age on purpose:
the other way round, the first run after a SIGKILL would always exit 2.

ponytail: a lock FILE with a stale-age escape rather than fcntl, because the cockpit is also
written by shell and by hand; move to flock if this ever guards more than markdown.
"""
from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import time
from pathlib import Path

_HELD: dict[Path, str] = {}                  # lock path -> this process's ownership token
_STALE_AFTER, _WAIT_TRIES = 30, 800          # abandoned after 30s, ~40s of waiting


class LockError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


def _claim(lock: Path, mine: str) -> bool:
    """Create the lock carrying who holds it, or steal one nobody is coming back for."""
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        with contextlib.suppress(OSError):
            if time.time() - lock.stat().st_mtime > _STALE_AFTER:
                lock.unlink()
        return False
    os.write(fd, mine.encode())
    os.close(fd)
    return True


@contextlib.contextmanager
def locked(path: Path):
    """Hold the write lock for `path`, or refuse. Never proceeds unlocked."""
    lock, mine = path.with_suffix(path.suffix + ".lock"), f"{os.getpid()}:{time.time_ns()}"
    for _ in range(_WAIT_TRIES):
        if _claim(lock, mine):
            _HELD[lock] = mine
            break
        time.sleep(0.05)
    else:                                    # proceeding unlocked IS the lost update
        raise LockError("LOCKED", f"{lock} held by another writer — nothing was written")
    try:
        yield
    finally:
        _HELD.pop(lock, None)
        with contextlib.suppress(OSError):
            if lock.read_text() == mine:     # only ever the one this process still holds
                lock.unlink()


def still_mine(path: Path) -> None:
    """Refuse to write once the lock has been stolen. Owning it at t=0 proves nothing."""
    lock = path.with_suffix(path.suffix + ".lock")
    with contextlib.suppress(OSError):
        if _HELD.get(lock) and lock.read_text() == _HELD[lock]:
            return
    raise LockError("LOCK_LOST", f"{lock} was taken by another writer while this one held it "
                                 "— nothing was written")


def write_atomic(path: Path, body: str) -> None:
    """Same directory, then rename: a reader never sees a half-written file."""
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(body)
    os.replace(tmp, path)


def _selfcheck_steal(f: Path) -> list[bool]:
    """A lock stolen mid-hold: the write must refuse, and our exit must not remove it."""
    lock, ok = f.with_suffix(f.suffix + ".lock"), []
    with locked(f):
        ok.append(lock.read_text().startswith(f"{os.getpid()}:"))
        still_mine(f)                            # ours: must not raise
        lock.write_text("thief:1")
        try:
            still_mine(f)
            ok.append(False)                     # must have raised
        except LockError as exc:
            ok.append(exc.code == "LOCK_LOST")
    ok.append(lock.read_text() == "thief:1")     # the thief's lock survived our exit
    lock.unlink()
    return ok


def cmd_selfcheck() -> int:
    """The branches that lose data if they regress."""
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "s.md"
        f.write_text("x\n")
        ok = _selfcheck_steal(f)
        write_atomic(f, "y\n")
        ok.append(f.read_text() == "y\n" and not list(Path(d).glob("*.tmp")))
        ok.append(_WAIT_TRIES * 0.05 > _STALE_AFTER)  # or a run after a kill always exits 2
    print(f"state_lock selfcheck: {sum(ok)}/{len(ok)} branches OK")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(cmd_selfcheck())
