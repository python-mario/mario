# pylint: disable=protected-access

from __future__ import generator_stop

import collections
import os
import string
import urllib
import subprocess
import time

import click.testing
import pytest
import hypothesis
import hypothesis.strategies as st


import pype
import pype.app
import pype._version
from tests import config

hypothesis.settings.register_profile("ci", max_examples=1000)
hypothesis.settings.register_profile("dev", max_examples=10)
hypothesis.settings.register_profile(
    "debug", max_examples=10, verbosity=hypothesis.Verbosity.verbose
)
hypothesis.settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


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
    "command_string,symbol,expected",
    [
        ("int", "?", "int(?)"),
        ("int(?)", "?", "int(?)"),
        ("str.upper", "?", "str.upper(?)"),
        ("str.upper(?)", "?", "str.upper(?)"),
        ("int", "$", "int($)"),
    ],
)
def test_add_short_placeholder(command_string, symbol, expected):
    assert pype.app._add_short_placeholder(command_string, symbol) == expected


def test_command_string_to_function():
    assert pype.app._command_string_to_function("int")("4") == 4
    assert pype.app._command_string_to_function("str.upper")("abc") == "ABC"


@pytest.mark.parametrize(
    "pipestring, modules, value, expected",
    [
        ("str.upper", None, "abc", "ABC"),
        ('str.upper ! ? + "z" ', None, "abc", "ABCz"),
        ('str.upper ! ? + "z" ! set', None, "abc", set("ABCz")),
        (
            "str.upper ! collections.Counter ! dict",
            {"collections": collections},
            "abbccc",
            {"A": 1, "B": 2, "C": 3},
        ),
    ],
)
def test_pipestring_to_function(pipestring, modules, value, expected):
    assert pype.app._pipestring_to_function(pipestring, modules)(value) == expected


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
    assert pype.app._get_autoimport_modules(name) == expected


@pytest.mark.parametrize(
    "string, expected",
    [
        ("a", {"a"}),
        ("?.upper", set()),
        ("map", {"map"}),
        ("map(json.dumps)", {"map", "json.dumps"}),
        ("collections.Counter(?)", {"collections.Counter"}),
        ("urllib.parse.urlparse", {"urllib.parse.urlparse"}),
        ("1 + 2", set()),
        ("json.dumps(collections.Counter)", {"json.dumps", "collections.Counter"}),
        ('str.__add__(?, "bc") ', {"str.__add__"}),
        ("? and time.sleep(1)", {"and", "time.sleep"}),
    ],
)
def test_get_identifiers(string, expected):
    result = pype.app._get_maybe_namespaced_identifiers(string)
    assert result == expected


def test_cli_raises_without_autoimport(runner):

    args = [
        "--no-autoimport",
        "map",
        'str.replace(?, ".", "!") ! collections.Counter ! json.dumps ',
    ]
    in_stream = "a.b.c\n"

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, NameError)


def test_cli_works_with_multiline_command(runner):

    args = [
        "--no-autoimport",
        "map",
        """
        (
         'x'
         + ?
        )
        """,
    ]
    in_stream = "a\n"

    result = runner.invoke(pype.app.cli, args, input=in_stream)
    assert not result.exception
    assert result.stdout == "xa\n"


def test_raises_on_missing_module(runner):

    args = [
        "map",
        '_missing_module.replace(?, ".", "!") ! collections.Counter ! json.dumps ',
    ]
    in_stream = "a.b.c\n"

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, NameError)


@pytest.mark.parametrize(
    "mapper",
    [
        str.capitalize,
        str.casefold,
        str.expandtabs,
        str.isalnum,
        str.isalpha,
        str.isdecimal,
        str.isdigit,
        str.isidentifier,
        str.islower,
        str.isnumeric,
        str.isprintable,
        str.isspace,
        str.istitle,
        str.isupper,
        str.lower,
        str.lstrip,
        str.rsplit,
        str.rstrip,
        str.split,
        str.splitlines,
        str.strip,
        str.swapcase,
        str.title,
        str.upper,
    ],
)
@hypothesis.given(string=st.text())
def test_str_simple_mappers(mapper, string):

    expected = [mapper(string)]
    qualname = mapper.__qualname__
    result = list(pype.app.run(qualname, in_stream=[string], newlines=False))

    assert result == expected


@pytest.mark.parametrize("mapper", [int.bit_length])
@hypothesis.given(in_stream=st.integers())
def test_main_mappers_int(mapper, in_stream):
    qualname = mapper.__qualname__
    result = list(pype.app.run(qualname, in_stream=[in_stream], newlines=False))

    expected = [mapper(in_stream)]

    assert result == expected


def assert_exception_equal(e1, e2):
    assert type(e1) == type(e2)
    assert e1.args == e2.args


@pytest.mark.parametrize("option", ["--invented-option", "-J"])
def test_raises_on_nonexistent_option(option, runner):
    args = [option, "print"]
    in_stream = "a.b.c\n"

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert_exception_equal(result.exception, SystemExit(2))


@pytest.mark.xfail(strict=True)
@hypothesis.given(st.text())
def test_get_identifiers_matches_str_isidentifier(string):
    identifiers = pype.app._get_maybe_namespaced_identifiers(string)
    assert all([identifier.isidentifier() for identifier in identifiers])


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"mapper": "str.upper", "newlines": False, "in_stream": ["abc"]}, ["ABC"]),
        ({"mapper": "str.upper", "newlines": True, "in_stream": ["abc"]}, ["ABC"]),
        (
            {
                "mapper": "collections.Counter ! ?.keys() ",
                "in_stream": ["abbccc\n"],
                "newlines": False,
            },
            [{"a": 1, "b": 2, "c": 3, "\n": 1}.keys()],
        ),
        (
            {
                "mapper": 'collections.Counter ! ?.keys() ! "".join ',
                "in_stream": ["abbccc\n"],
                "newlines": False,
            },
            ["abc\n"],
        ),
        (
            {
                "mapper": 'collections.Counter ! ?.keys() ! "".join ',
                "in_stream": [""],
                "newlines": False,
            },
            [""],
        ),
        (
            {"mapper": 'str.__add__(?, "bc")', "newlines": False, "in_stream": ["a"]},
            ["abc"],
        ),
        (
            {
                "newlines": False,
                "applier": "functools.partial(map, str.upper)",
                "in_stream": ["a\nbb\nccc\n"],
            },
            ["A\nBB\nCCC\n"],
        ),
        (
            {
                "newlines": False,
                "applier": "? or time.sleep(1)",
                "in_stream": ["a\nbb\nccc\n"],
            },
            ["a\nbb\nccc\n"],
        ),
        ({"newlines": False, "mapper": "?", "in_stream": ["\r"]}, ["\r"]),
    ],
)
def test_main_example(kwargs, expected):
    result = pype.app.run(**kwargs)
    assert list(result) == expected


def test_lambda():
    mapper = "str.split ! sorted(?, key=lambda x: x[-1])"
    in_stream = ["1 2\n2 1\n"]
    result = pype.app.run(mapper=mapper, newlines=False, in_stream=in_stream)
    expected = [["1", "1", "2", "2"]]
    assert list(result) == expected


def test_keyword_arg():
    mapper = "str.split ! sorted(?, key=operator.itemgetter(-1))"
    in_stream = ["1 2\n2 1\n"]
    result = pype.app.run(mapper=mapper, newlines=False, in_stream=in_stream)
    expected = [["1", "1", "2", "2"]]
    assert list(result) == expected


@pytest.mark.parametrize(
    "command, placeholder, expected",
    [
        ("?", "?", pype.app._PYPE_VALUE),
        ('"?"', "?", '"?"'),
        ('f"{?}"', "?", 'f"{' + pype.app._PYPE_VALUE + '}"'),
    ],
)
def test_replace_short_placeholder_parso(command, placeholder, expected):
    result = pype.app._replace_short_placeholder(command, placeholder)
    assert result == expected


def test_main_f_string():

    result = list(pype.app.main("""f'"{?}"'""", in_stream=["abc"], newlines="no"))
    assert result == ['"abc"']


@hypothesis.given(string=st.text())
def test_fn_autoimport_counter_keys(string):
    mapper = "collections.Counter ! ?.keys() "
    string = string + "\n"
    in_stream = [string]
    expected = [(collections.Counter(string).keys())]
    result = pype.app.run(mapper=mapper, in_stream=in_stream, newlines=False)
    assert list(result) == expected


@pytest.mark.parametrize(
    "args,expected",
    [
        ((["ab"], "auto", True), ["ab\n"]),
        ((["ab"], "auto", False), ["ab"]),
        ((["ab"], True, True), ["ab\n"]),
        ((["ab"], False, True), ["ab"]),
        ((["ab"], True, False), ["ab\n"]),
        ((["ab\n", "cd\n"], "auto", True), ["ab\n", "cd\n"]),
        ((["ab\n", "cd\n"], True, True), ["ab\n\n", "cd\n\n"]),
        ((["ab\n", "cd\n"], False, True), ["ab\n", "cd\n"]),
    ],
)
def test_maybe_add_newlines(args, expected):
    text, input_setting, input_has_newlines = args
    assert (
        list(pype.app._maybe_add_newlines(text, input_setting, input_has_newlines))
        == expected
    )


@hypothesis.given(string=st.one_of(st.just(""), st.text()))
def test_main_autoimport_placeholder_does_not_raise(string):
    mapper = 'collections.Counter ! ?.keys() ! "".join '
    pype.app.main(mapper=mapper, in_stream=[string])


@pytest.mark.parametrize("string", ["", "\n", "a", "a\n"])
def test_cli_autoimport_placeholder(string, runner):
    args = ["--newlines=no", "map", 'str ! collections.Counter ! ?.keys() ! "".join ']

    in_stream = string

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    expected = "".join(collections.Counter(in_stream).keys())
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == expected


@pytest.mark.parametrize(
    "args, in_stream, expected",
    [
        (["map", "?"], "abc", "abc"),
        (["map", 'str.replace(?, ".", "!")'], "a.b.c\n", "a!b!c\n"),
        (["--placeholder=$", "map", 'str.replace($, ".", "!")'], "a.b.c\n", "a!b!c\n"),
        (
            [
                "-icollections",
                "-ijson",
                "--newlines=no",
                "map",
                'json.dumps(dict(collections.Counter(str.replace(?, ".", "!"))))',
            ],
            "a.b.c",
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                "-icollections",
                "-ijson",
                "--newlines=yes",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter(?) ! dict(?) ! json.dumps(?) ',
            ],
            "a.b.c\n",
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                "-icollections",
                "-ijson",
                "--newlines=yes",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter ! dict ! json.dumps ',
            ],
            "a.b.c\n",
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                "-icollections",
                "-ijson",
                "--newlines=yes",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter ! json.dumps ',
            ],
            "a.b.c\nd.e.f\n",
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n{"d": 1, "!": 2, "e": 1, "f": 1, "\\n": 1}\n',
        ),
        (
            [
                "--newlines=yes",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter(?) ! json.dumps(?) ',
            ],
            "a.b.c\n",
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                "--newlines=yes",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter ! dict ! json.dumps ',
            ],
            "a.b.c\n",
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                "--newlines=no",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter ! dict ! json.dumps ',
            ],
            "a.b.c",
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                "--newlines=yes",
                "apply",
                "enumerate ! list ! reversed ! enumerate ! list",
            ],
            "a\nbb\nccc\n",
            "[(0, (2, 'ccc\\n')), (1, (1, 'bb\\n')), (2, (0, 'a\\n'))]\n",
        ),
        (
            ["--newlines=no", "apply", "functools.partial(map, str.upper)"],
            "a\nbb\nccc\n",
            "A\nBB\nCCC\n",
        ),
        (
            [
                "--newlines=no",
                "map",
                'str.replace(?, ".", "!") ! collections.Counter ! dict ! json.dumps ',
            ],
            "a.b.c",
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            ["--newlines=no", "map", "? or collections.Counter(?)"],
            "a\nbb\nccc\n",
            "a\nbb\nccc\n",
        ),
        (
            [
                "apply",
                "itertools.islice(?, 1, 3)",
                "map",
                "toolz.first",
                "apply",
                '", ".join(?)',
            ],
            "a\nbb\nccc\ndddd\n",
            "b, c\n",
        ),
        (["stack", "len"], "a\nbb\n", "5\n"),
        (["list", "len"], "a\n\bb\n", "2\n"),
    ],
)
def test_cli(args, in_stream, expected, runner):

    result = runner.invoke(pype.app.cli, args, input=in_stream)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == expected


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
        ('str.upper ! ? + "z"', "!", ["str.upper", ' ? + "z"']),
    ],
)
def test_split_string_on_separator(string, separator, expected):
    result = list(pype.app._split_string_on_separator(string, separator))
    assert result == expected


class Timer:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        self.end = time.monotonic()
        self.elapsed = self.end - self.start


def test_cli_async(runner, reactor, server):
    base_url = "http://localhost:8080/{}"
    letters = string.ascii_lowercase
    in_stream = "\n".join(base_url.format(c) for c in letters)
    command = "str.upper ! ?.rstrip() ! treq.get ! treq.text_content "
    args = ["--max-concurrent", "100", "--async", "map", command]
    expected = [f"Hello, {letter.upper()}" for letter in letters]

    with Timer() as t:
        result = runner.invoke(pype.app.cli, args, input=in_stream)

    lines = result.output.splitlines()
    starts = [line[:8] for line in lines]
    sorted_starts = sorted(starts)

    assert not result.exception
    assert result.exit_code == 0
    assert sorted_starts == expected
    limit_seconds = 4.0
    assert t.elapsed < limit_seconds

@pytest.mark.skip
def test_cli_async_chain_map_apply(runner, reactor, server):
    base_url = "http://localhost:8080/{}"
    letters = string.ascii_lowercase
    in_stream = "\n".join(base_url.format(c) for c in letters)
    mapper = "str.upper ! ?.rstrip() ! treq.get ! treq.text_content "
    applier = "max"
    args = ["--async", "map", mapper, "apply", applier]
    expected = ["Hello, Z"]

    with Timer() as t:
        result = runner.invoke(pype.app.cli, args, input=in_stream)

    lines = result.output.splitlines()
    starts = [line[:8] for line in lines]

    assert not result.exception
    assert result.exit_code == 0
    assert len(lines) == 1
    assert starts == expected
    limit_seconds = 4.0
    assert t.elapsed < limit_seconds


def test_cli_version(runner):
    args = ["--version"]

    result = runner.invoke(pype.app.cli, args)

    assert result.output == f"{pype.__name__} {pype._version.__version__}\n"
    assert not result.exception
    assert result.exit_code == 0
