import collections
import os.path
import urllib.parse

import lxml.etree
import pytest
from tests import helpers

from mario import interpret


SYMBOL = "x"


def test_split_pipestring():
    s = 'x ! y + f"{x!r}"'
    sep = "!"
    assert interpret.split_pipestring(s, sep) == ["x", ' y + f"{x!r}"']


@pytest.mark.parametrize(
    "name, expected",
    [
        ("str.upper", {}),
        ("os.path.join", {"os": os, "os.path": os.path}),
        ("map", {}),
        ("collections.Counter", {"collections": collections}),
        ("urllib.parse.urlparse", {"urllib": urllib, "urllib.parse": urllib.parse}),
        ("lxml.etree.parse", {"lxml": lxml, "lxml.etree": lxml.etree}),
    ],
)
def test_get_module(name, expected):
    assert interpret.build_name_to_module(name) == expected


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
    result = list(interpret.split_pipestring(string, separator))
    assert result == expected


def test_no_autocall():
    output = helpers.run(["map", "--no-autocall", "1"], input=b"a\nbb\n").decode()
    assert output == "1\n1\n"


def test_autocall():
    output = helpers.run(["map", "len"], input=b"a\nbb\n").decode()
    assert output == "1\n2\n"


def test_autocall_in_eval():
    helpers.run(["eval", "datetime.datetime.now().isoformat()"]).decode()


def test_autocall_requires_symbol():
    output = helpers.run(["map", "pathlib.Path(x).name"], input=b"a\nbb\n").decode()
    assert output == "a\nbb\n"
