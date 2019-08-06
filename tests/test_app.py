# pylint: disable=protected-access
# pylint: disable=unused-argument

from __future__ import generator_stop

import os
import subprocess
import sys
import textwrap

import hypothesis
import pytest
from tests import helpers

import mario
import mario.app
import mario.cli
from mario import utils


hypothesis.settings.register_profile("ci", max_examples=1000)
hypothesis.settings.register_profile("dev", max_examples=10)
hypothesis.settings.register_profile(
    "debug", max_examples=10, verbosity=hypothesis.Verbosity.verbose
)
hypothesis.settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


def assert_exception_equal(e1, e2):
    # pylint: disable=unidiomatic-typecheck
    assert type(e1) == type(e2)
    assert e1.args == e2.args


@pytest.mark.parametrize("option", ["--invented-option", "-J"])
def test_raises_on_nonexistent_option(option, runner):
    args = [option, "print"]
    in_stream = "a.b.c\n"

    result = runner.invoke(mario.cli.cli, args, input=in_stream)
    assert result.exception


def test_eval_main(capsys):
    mario.app.main([[{"name": "eval", "code": "1+1", "parameters": {}}]])
    assert capsys.readouterr().out == "2\n"


def test_eval_cli():
    assert helpers.run(["eval", "1+1"]).decode() == "2\n"


def test_chain():
    expected = "[1, 2]\n"
    result = helpers.run(["eval", "[[1, 2]]", "chain"]).decode()
    assert result == expected, (result, expected)


def test_cli_version(runner):
    args = ["--version"]
    result = helpers.run(args).decode()
    assert result == f"mario, version {mario.__version__}\n"


def test_config_file(tmp_path):
    config_body = """
    exec_before = "from collections import Counter as C"
    """

    config_file_path = tmp_path / "config.toml"

    config_file_path.write_text(config_body)

    args = ["apply", "C(x)"]
    stdin = "1\n2\n".encode()
    env = dict(os.environ)
    env.update({f"{utils.NAME}_CONFIG_DIR".upper().encode(): str(tmp_path).encode()})
    output = helpers.run(args, input=stdin, env=env).decode()
    assert output.startswith("Counter")


def test_exec_before():
    exec_before = textwrap.dedent(
        """\
    import csv
    def func(line):
        return next(csv.reader([line]))
    """
    )

    assert (
        helpers.run(
            ["--exec-before", exec_before, "map", "func"], input=b"a,b\n"
        ).decode()
        == "['a', 'b']\n"
    )


def test_stage_exec_before():
    assert helpers.run(["eval", "--exec-before", "a=1", "a"]).decode() == "1\n"


def test_meta_pip_command():
    """``meta pip`` command accepts pip subcommands and options."""
    result = helpers.run(["meta", "pip", "install", "--help"]).decode()
    expected = (
        "pip install [options] <requirement specifier> [package-index-options] ..."
    )
    assert expected in result


def test_meta_test_command_fail(tmp_path, tmp_env):
    """Get a failing result when a test fails."""

    text = r"""
    [[command]]
    name = "mario-failing-test"
    short_help = "An internal test command for mario"
    help = "An internal test command for mario"

    [[command.stages]]
    command = "eval"
    params = {code="1"}

    [[command.tests]]
    invocation = ["mario-failing-test"]
    input = ""
    output = "2\n"

    """
    (tmp_path / "config.toml").write_text(text)

    proc = subprocess.run(
        [sys.executable, "-m", "python", "meta", "test", "-vvvvv", "-pno:sugar"],
        env=tmp_env,
        check=False,
        capture_output=True,
    )
    assert proc.returncode != 0


def test_meta_test_command_pass(tmp_path, tmp_env):
    """Get a failing result when a test fails."""

    text = r"""
    [[command]]
    name = "mario-passing-test"
    short_help = "An internal test command for mario"
    help = "An internal test command for mario"

    [[command.stages]]
    command = "eval"
    params = {code="1"}

    [[command.tests]]
    invocation = ["mario-passing-test"]
    input = ""
    output = "1\n"
    """
    (tmp_path / "config.toml").write_text(text)

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mario",
            "meta",
            "test",
            "-vvvv",
            "-pno:sugar",
            "--tb=long",
        ],
        env=tmp_env,
        capture_output=True,
    )
    assert proc.returncode == 0
