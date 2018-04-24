# pylint: disable=protected-access

from __future__ import generator_stop

import collections

import os
import urllib

import pytest
from click.testing import CliRunner
from hypothesis import given
import hypothesis.strategies as st
from hypothesis import settings, Verbosity, reproduce_failure

import pype
import pype.app
from pype.app import _PYPE_VALUE

settings.register_profile("ci", max_examples=1000)
settings.register_profile("dev", max_examples=10)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))


@pytest.fixture(name='runner')
def _runner():
    return CliRunner()


@pytest.mark.parametrize(
    'command, expected',
    [
        ('str.upper(?)', [f'str.upper({_PYPE_VALUE})']),
        ('str.upper', [f'str.upper({_PYPE_VALUE})']),
        ('str.upper(?) || "X".join', [f'str.upper({_PYPE_VALUE})', f'"X".join({_PYPE_VALUE})']),
    ],
)
def test_make_pipeline(command, expected):
    assert pype.app._make_pipeline_strings(command, '?') == expected


@pytest.mark.parametrize(
    'name, expected',
    [
        ('str.upper', {}),
        ('os.path.join', {'os.path': os.path}),
        ('map', {}),
        ('collections.Counter', {'collections': collections}),
        ('urllib.parse.urlparse', {'urllib.parse': urllib.parse}),
    ],
)
def test_get_module(name, expected):
    assert pype.app._get_autoimport_modules(name) == expected


@pytest.mark.parametrize(
    'string, expected',
    [
        ('a', {'a'}),
        ('?.upper', set()),
        ('map', {'map'}),
        ('map(json.dumps)', {'map', 'json.dumps'}),
        ('collections.Counter(?)', {'collections.Counter'}),
        ('urllib.parse.urlparse', {'urllib.parse.urlparse'}),
        ('1 + 2', set()),
        ('json.dumps(collections.Counter)', {'json.dumps', 'collections.Counter'}),
        ('str.__add__(?, "bc") ', {'str.__add__'}),
    ],
)
def test_get_identifiers(string, expected):
    assert pype.app._get_maybe_namespaced_identifiers(string) == expected


def test_cli_raises_without_autoimport(runner):

    args = [
        '--no-autoimport',
        'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
    ]
    in_stream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, NameError)


def test_raises_on_missing_module(runner):

    args = [
        '_missing_module.replace(?, ".", "!") || collections.Counter || json.dumps ',
    ]
    in_stream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, RuntimeError)


@pytest.mark.parametrize(
    'mapper',
    [
        str.capitalize, str.casefold, str.expandtabs, str.isalnum, str.isalpha, str.isdecimal,
        str.isdigit, str.isidentifier, str.islower, str.isnumeric, str.isprintable, str.isspace,
        str.istitle, str.isupper, str.lower, str.lstrip, str.rsplit, str.rstrip, str.split,
        str.splitlines, str.strip, str.swapcase, str.title, str.upper
    ],
)
@given(string=st.text())
def test_str_simple_mappers(mapper, string):

    expected = [str(mapper(string)) + '\n']
    qualname = mapper.__qualname__
    result = list(pype.app.main(qualname, in_stream=[string], newlines='yes'))

    assert result == expected


@pytest.mark.parametrize(
    'mapper',
    [
        int.bit_length,
    ],
)
@given(in_stream=st.integers())
def test_main_mappers_int(mapper, in_stream):
    qualname = mapper.__qualname__
    result = list(pype.app.main(qualname, in_stream=[in_stream]))

    expected = [str(mapper(in_stream)) + '\n']

    assert result == expected


def assert_exception_equal(e1, e2):
    assert type(e1) == type(e2)
    assert e1.args == e2.args


@pytest.mark.parametrize(
    'option',
    [
        '--invented-option',
        '-J',
    ],
)
def test_raises_on_nonexistent_option(option, runner):
    args = [
        option,
        'print',
    ]
    in_stream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert_exception_equal(result.exception, SystemExit(2, ))


@pytest.mark.xfail(strict=True)
@given(st.text())
def test_get_identifiers_matches_str_isidentifier(string):
    identifiers = pype.app._get_maybe_namespaced_identifiers(string)
    assert all([identifier.isidentifier() for identifier in identifiers])


@pytest.mark.parametrize(
    'kwargs,expected',
    [
        (
            {
                'mapper': 'collections.Counter || ?.keys() ',
                'in_stream': ['abbccc\n'],
            },
            [str({'a': 1, 'b': 2, 'c': 3, '\n': 1}.keys()) + '\n'],
        ),
        (
            {
                'mapper': 'collections.Counter || ?.keys() || "".join ',
                'in_stream': ['abbccc\n'],
            },
            ['abc\n'],
        ),
        (
            {
                'mapper': 'collections.Counter || ?.keys() || "".join ',
                'in_stream': [''],
            },
            ['\n'],
        ),
        (
            {
                'mapper': 'str.__add__(?, "bc")',
                'newlines': 'yes',
                'in_stream': ['a'],
            },
            ['abc\n'],
        ),
    ],
)
def test_main_example(kwargs, expected):
    result = pype.app.main(**kwargs)
    assert list(result) == expected


@given(string=st.text())
def test_fn_autoimport_counter_keys(string):
    mapper = 'collections.Counter || ?.keys() '
    string = string + '\n'
    in_stream = [string]
    expected = [str(collections.Counter(string).keys()) + '\n']
    result = pype.app.main(mapper=mapper, in_stream=in_stream)
    assert list(result) == expected


@pytest.mark.parametrize(
    'args,expected',
    [
        ((['ab'], ), ['ab\n']),
        ((['ab'], 'auto'), ['ab\n']),
        ((['ab'], 'yes'), ['ab\n']),
        ((['ab'], 'no'), ['ab']),
        ((['ab', 'cd'], 'auto'), ['ab\n', 'cd\n']),
        ((['ab', 'cd'], 'yes'), ['ab\n', 'cd\n']),
        ((['ab', 'cd'], 'no'), ['ab', 'cd']),
    ],
)
def test__maybe_add_newlines(args, expected):
    assert list(pype.app._maybe_add_newlines(*args)) == expected


@given(string=st.one_of(st.just(''), st.text()))
def test_main_autoimport_placeholder_does_not_raise(string):
    mapper = 'collections.Counter || ?.keys() || "".join '
    pype.app.main(mapper=mapper, in_stream=[string])


@given(string=st.text())
def test_cli_autoimport_placeholder(string, runner):
    args = [
        '--newlines=yes',
        'str || collections.Counter || ?.keys() || "".join ',
    ]

    in_stream = string + '\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    expected = ''.join(collections.Counter(in_stream).keys()) + '\n'
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == expected


@pytest.mark.parametrize(
    'args, in_stream, expected',
    [
        ([
            'str.replace(?, ".", "!")',
            '?',
            '?',
        ], 'a.b.c\n', 'a!b!c\n'),
        ([
            '--placeholder=$',
            'str.replace($, ".", "!")',
            '$',
            '$',
        ], 'a.b.c\n', 'a!b!c\n'),
        (
            [
                '-icollections',
                '-ijson',
                'json.dumps(dict(collections.Counter(str.replace(?, ".", "!"))))',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                'str.replace(?, ".", "!") || collections.Counter(?) || dict(?) || json.dumps(?) ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
            ],
            'a.b.c\nd.e.f\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n{"d": 1, "!": 2, "e": 1, "f": 1, "\\n": 1}\n',
        ),
        (
            [
                ' str.replace(?, ".", "!") || collections.Counter',
                'toolz.merge_with(sum, ?)',
            ],
            "a.b.c\nd.e.f\n",
            "{'a': 1, '!': 4, 'b': 1, 'c': 1, '\\n': 2, 'd': 1, 'e': 1, 'f': 1}\n",
        ),
        (
            [
                'str.replace(?, ".", "!") || collections.Counter(?) || json.dumps(?) ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--slurp',
                'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
            ],
            'a.b.c\nd.e.f\n',
            '{"a": 1, "!": 4, "b": 1, "c": 1, "\\n": 2, "d": 1, "e": 1, "f": 1}\n',
        ),
        (
            [
                '--slurp',
                'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
            ],
            'a.b.c\nd.e.f\n',
            '{"a": 1, "!": 4, "b": 1, "c": 1, "\\n": 2, "d": 1, "e": 1, "f": 1}\n',
        ),
        (
            [
                '--newlines=yes',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '--newlines=no',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}',
        ),
    ],
)
def test_cli(args, in_stream, expected, runner):

    result = runner.invoke(pype.app.cli, args, input=in_stream)
    assert not result.exception
    assert result.output == expected
