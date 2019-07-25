# pylint: disable=unused-argument

import subprocess
import sys
import time

import pytest
import requests

from . import helpers


@pytest.fixture(name="reactor")
def _reactor():
    from twisted.internet import reactor

    return reactor


@pytest.fixture(name="server")
def _server():
    # pylint: disable=fixme
    # TODO Replace subprocess with reactor
    command = [sys.executable, "-m", "tests.server"]
    proc = subprocess.Popen(command, stderr=subprocess.PIPE)
    time.sleep(1)
    yield
    proc.terminate()


def test_server(server):
    assert requests.get("http://localhost:8080/?delay=1")


def test_cli_async_map_then_apply(runner, reactor, server):
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [1, 2, 3, 4, 5] * 9)

    args = [
        "-m",
        "mario",
        "--max-concurrent",
        "100",
        "async-map",
        "await asks.get(x) ! x.json()",
        "filter",
        'x["id"] % 6 == 0',
        "map",
        "x['id']",
        "apply",
        "max(x)",
    ]

    expected = "42\n"
    limit_seconds = 6.0
    with helpers.Timer() as t:
        output = subprocess.check_output(
            [sys.executable, *args], input=in_stream.encode(), timeout=limit_seconds
        ).decode()

    assert output == expected
    assert t.elapsed < limit_seconds


def test_cli_async_map(runner, reactor, server, capsys):
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [1, 1, 5, 1])

    args = [
        "--exec-before",
        "import datetime; now=datetime.datetime.now; START_TIME=now()",
        "async-map",
        'await asks.get !  f"{types.SimpleNamespace(**x.json()).delay}"',
    ]

    expected = "1\n1\n5\n1\n"

    with helpers.Timer() as t:
        output = helpers.run(args, input=in_stream.encode()).decode()

    assert output == expected
    limit_seconds = 6.0
    assert t.elapsed < limit_seconds


def test_cli_async_map_unordered(runner, reactor, server, capsys):
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [5, 2, 3, 1, 4])

    args = [
        "async-map-unordered",
        'await asks.get !  f"{types.SimpleNamespace(**x.json()).delay}"',
    ]

    expected = "1\n2\n3\n4\n5\n"

    with helpers.Timer() as t:
        output = helpers.run(args, input=in_stream.encode()).decode()

    assert output == expected
    limit_seconds = 7.0
    assert t.elapsed < limit_seconds


def test_cli_async_reduce_fails(runner, reactor, server, capsys):
    """``reduce`` takes the name of a function as its argument, and fails otherwise."""
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [6, 2, 1])

    args = ["map", "json.loads", "reduce", "toolz.curry(operator.truediv)(*x)"]

    with pytest.raises(subprocess.CalledProcessError):
        helpers.run(args, input=in_stream.encode()).decode()


def test_cli_async_reduce_without_curry(runner, reactor, server, capsys):
    base_url = "http://localhost:8080/?delay={}\n"

    in_stream = "".join(base_url.format(i) for i in [6, 2, 1])

    args = [
        "async-map",
        'await asks.get !  f"{types.SimpleNamespace(**x.json()).delay}"',
        "map",
        "json.loads",
        "reduce",
        "operator.truediv",
    ]

    expected = "3.0\n"

    with helpers.Timer() as t:
        output = helpers.run(args, input=in_stream.encode()).decode()

    assert output == expected
    limit_seconds = 7.0
    assert t.elapsed < limit_seconds
