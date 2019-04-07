import os
import collections
import urllib.parse

import pytest


from pype import interpret

from tests import tools

SYMBOL = "x"


def test_split_pipestring():
    s = 'x ! y + f"{x!r}"'
    sep = "!"
    assert interpret.split_pipestring(s, sep) == ["x", ' y + f"{x!r}"']


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


def test_autocall():
    output = tools.run(["--autocall", "map", "len"], input=b"a\nbb\n").decode()
    assert output == "1\n2\n"
