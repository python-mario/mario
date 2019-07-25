import pathlib
import subprocess
import sys
import time

import attr

import mario.exceptions


TESTS_DIR = pathlib.Path(__file__).parent


def run(args, capture_output=True, check=True, **kwargs):
    args = [sys.executable, "-m", "mario"] + args
    proc = subprocess.run(args, capture_output=capture_output, check=check, **kwargs)
    return proc.stdout


@attr.s(auto_exc=True)
class TimerMaxExceeded(mario.exceptions.MarioException):
    """Raised if the timer max is exceeded."""

    timer = attr.ib()


@attr.s
class Timer:
    """Time the body of the context manager.


    Args:
        max (float): Maximum allowed time. An exception will be raised if the
                     total duration exceeded this value. The body will not be
                     interrupted by the timer; ``max`` is only checked
                     afterwards.
        elapsed (float): Total elapsed seconds during the context manager body.
                         Set to ``None`` until the context manager exits.


    Raises:
        TimerMaxExceeded: If the maximum is exceeded when the context manager
                          exits.
    """

    max = attr.ib(default=float("inf"))
    elapsed = attr.ib(default=None)
    _start = attr.ib(default=None)
    _end = attr.ib(default=None)

    def __enter__(self):
        self._start = time.monotonic()
        return self

    def __exit__(self, *args):
        self._end = time.monotonic()
        self.elapsed = self._end - self._start

        if self.elapsed > self.max:
            raise TimerMaxExceeded(self)
