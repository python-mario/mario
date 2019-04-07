import subprocess
import sys
import time
import string


import pytest

from . import config


@pytest.fixture(name="reactor")
def _reactor():
    from twisted.internet import reactor

    return reactor


@pytest.fixture(name="server")
def _server():
    # TODO Replace subprocess with reactor
    command = ["python", config.TEST_DIR / "server.py"]
    proc = subprocess.Popen(command)
    time.sleep(1)
    yield
    proc.terminate()


class Timer:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.end = time.monotonic()
        self.elapsed = self.end - self.start


def test_cli_async_chain_map_apply(runner, reactor, server):
    base_url = "http://localhost:8080/{}\n"
    letters = string.ascii_uppercase
    in_stream = "".join(base_url.format(c) for c in letters)

    args = [
        "-m",
        "pype",
        "--max-concurrent",
        "100",
        "map",
        "await asks.get(x) ! x.text",
        "filter",
        "'Q' in x or 'T' in x",
        "apply",
        "max(x)",
        "map",
        "x.upper()",
    ]

    expected = "HELLO, T. YOU ARE CLIENT NUMBER 0 FOR THIS SERVER.\n"

    with Timer() as t:
        output = subprocess.check_output(
            [sys.executable, *args], input=in_stream.encode()
        ).decode()

    assert output == expected
    limit_seconds = 4.0
    assert t.elapsed < limit_seconds
