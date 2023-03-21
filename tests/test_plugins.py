"""Tests for mario addons."""

import subprocess
import sys

import attr
import docshtest
import pytest

import mario.declarative
import mario.plug
import mario.plugins


REGISTRY = mario.plug.make_plugin_commands_registry()
# pylint: disable=no-member
COMMANDS = REGISTRY.commands.values()
TEST_SPECS = [test_spec for command in COMMANDS for test_spec in command.tests]
REQUIRED_FIELDS = ["tests", "help", "short_help"]


def get_param_id(param):
    """Make a verbose id for a test parameter."""
    if attr.has(type(param)):
        return repr(attr.asdict(param))[:35]
    return repr(param)


command_parametrize = pytest.mark.parametrize("command", COMMANDS, ids=get_param_id)


@pytest.mark.parametrize("test_spec", TEST_SPECS, ids=get_param_id)
def test_command_test_spec(test_spec: mario.declarative.CommandTest):
    """The invocation and input generate the expected output."""
    # pylint: disable=unexpected-keyword-arg
    output = subprocess.check_output(
        [sys.executable, "-m", "mario"] + list(test_spec.invocation),
        input=test_spec.input.encode(),
    ).decode()
    assert output == test_spec.output


@command_parametrize
@pytest.mark.parametrize("field_name", REQUIRED_FIELDS, ids=get_param_id)
def test_command_has_required_fields(command, field_name):
    """Test that the command has all required fields."""
    attribute = getattr(command, field_name)
    assert attribute


@command_parametrize
def test_help(command):
    """The command help passes docshtest."""
    lines = command.help.splitlines(keepends=True)
    for line in lines:
        if line.startswith(" " * 2) and not line.startswith(" " * 4):
            raise IndentationError(f"Line starts with 2 spaces and not 4: \n{line}")
    docshtest.shtest_runner(lines, regex_patterns="")


@command_parametrize
def test_invocation_includes_command(command):
    """The test invocation actually includes the tested command."""

    for test in command.tests:
        message = f"The tested command {command.name} is not in the invocation {test.invocation}."
        assert command.name in test.invocation, message


@pytest.mark.xfail
def test_python_command_docstrings():
    """Run docshtest on docstrings of commands defined in Python code."""
    raise NotImplementedError
