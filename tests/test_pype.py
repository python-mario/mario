# pylint: disable=protected-access

from __future__ import generator_stop

import collections
import os
import string
import urllib
import subprocess
import time
import sys

import click.testing
import pytest
import hypothesis
import hypothesis.strategies as st


import pype
import pype.app
import pype.cli
import pype._version
from pype import utils
from tests import config


hypothesis.settings.register_profile("ci", max_examples=1000)
hypothesis.settings.register_profile("dev", max_examples=10)
hypothesis.settings.register_profile(
    "debug", max_examples=10, verbosity=hypothesis.Verbosity.verbose
)
hypothesis.settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))

SYMBOL = "x"


def run(args, **kwargs):
    args = [sys.executable, "-m", "pype"] + args
    return subprocess.check_output(args, **kwargs)


@pytest.fixture(name="runner")
def _runner():
    return click.testing.CliRunner()


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


@pytest.mark.parametrize(
    "name, expected",
    [
        ("str.upper", {}),
        ("os.path.join", {"os.path": os}),
        ("map", {}),
        ("collections.Counter", {"collections": collections}),
        ("urllib.parse.urlparse", {"urllib.parse": urllib}),
    ],
)
def test_get_module(name, expected):
    assert pype.app.build_name_to_module(name) == expected


def assert_exception_equal(e1, e2):
    assert type(e1) == type(e2)
    assert e1.args == e2.args


@pytest.mark.parametrize("option", ["--invented-option", "-J"])
def test_raises_on_nonexistent_option(option, runner):
    args = [option, "print"]
    in_stream = "a.b.c\n"

    result = runner.invoke(pype.cli.cli, args, input=in_stream)

    assert_exception_equal(result.exception, SystemExit(2))


@pytest.mark.parametrize(
    "string, separator, expected",
    [
        ("a", "!", ["a"]),
        ("ab", "!", ["ab"]),
        ("ab!cd", "!", ["ab", "cd"]),
        ("ab!cd!ef", "!", ["ab", "cd", "ef"]),
        ('a"b!c"d!ef', "!", ['a"b!c"d', "ef"]),
        ("a", "\\", ["a"]),
        ("ab", "\\", ["ab"]),
        ("ab\\cd", "\\", ["ab", "cd"]),
        ("ab\\cd\\ef", "\\", ["ab", "cd", "ef"]),
        ('a"b\\c"d\\ef', "\\", ['a"b\\c"d', "ef"]),
        (f'str.upper ! {SYMBOL} + "z"', "!", ["str.upper", f' {SYMBOL} + "z"']),
    ],
)
def test_split_string_on_separator(string, separator, expected):
    result = list(pype.app.split_pipestring(string, separator))
    assert result == expected


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


def test_eval(capsys):
    pype.app.main([("eval", "1+1")])
    assert capsys.readouterr().out == "2\n"


def test_stack():
    args = [sys.executable, "-m", "pype", "stack", "len(x)"]
    stdin = "1\n2\n".encode()
    output = subprocess.check_output(args, input=stdin).decode()
    assert output == "4\n"


def test_exec_before():
    args = [
        sys.executable,
        "-m",
        "pype",
        "--exec-before",
        "from collections import Counter as c",
        "stack",
        "c(x)",
    ]
    stdin = "1\n2\n".encode()
    output = subprocess.check_output(args, input=stdin).decode()
    assert output.startswith("Counter")


def test_cli_version(runner):
    args = ["--version"]

    result = runner.invoke(pype.cli.cli, args)

    assert result.output == f"pype, version {pype._version.__version__}\n"
    assert result.output.rstrip()[-1].isdigit()
    assert not result.exception
    assert result.exit_code == 0


def test_config_file(tmp_path):
    config_body = """
    exec_before = "from collections import Counter as C"
    """

    config_file_path = tmp_path / "config.toml"

    config_file_path.write_text(config_body)

    args = ["stack", "C(x)"]
    stdin = "1\n2\n".encode()
    env = dict(os.environ)
    env.update({f"{utils.NAME}_CONFIG_DIR".upper().encode(): str(tmp_path).encode()})
    output = run(args, input=stdin, env=env).decode()
    assert output.startswith("Counter")
