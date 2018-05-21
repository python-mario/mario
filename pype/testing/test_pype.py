# pylint: disable=protected-access

from __future__ import generator_stop

import collections
import os
import string
import urllib
import textwrap
from datetime import timedelta

import arrow
import pytest
from click.testing import CliRunner
from hypothesis import given
import hypothesis.strategies as st
from hypothesis import settings, Verbosity, reproduce_failure

import pype
import pype.app
import pype._version
from pype.app import _PYPE_VALUE, PypeParseError

settings.register_profile("ci", max_examples=1000)
settings.register_profile("dev", max_examples=10)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)
settings.load_profile(os.getenv('HYPOTHESIS_PROFILE', 'default'))


@pytest.fixture(name='runner')
def _runner():
    return CliRunner()


@pytest.fixture(name='reactor')
def _reactor():
    from twisted.internet import reactor
    return reactor


@pytest.mark.parametrize(
    'command_string,symbol,expected',
    [
        ('int', '?', 'int(?)'),
        ('int(?)', '?', 'int(?)'),
        ('str.upper', '?', 'str.upper(?)'),
        ('str.upper(?)', '?', 'str.upper(?)'),
        ('int', '$', 'int($)'),
    ],
)
def test_add_short_placeholder(command_string, symbol, expected):
    assert pype.app._add_short_placeholder(command_string, symbol) == expected


def test_command_string_to_function():
    assert pype.app._command_string_to_function('int')('4') == 4
    assert pype.app._command_string_to_function('str.upper')('abc') == 'ABC'


@pytest.mark.parametrize(
    'pipestring, modules, value, expected',
    [
        ('str.upper', None, 'abc', 'ABC'),
        ('str.upper || ? + "z" ', None, 'abc', 'ABCz'),
        ('str.upper || ? + "z" || set', None, 'abc', set('ABCz')),
        (
            'str.upper || collections.Counter || dict',
            {'collections': collections},
            'abbccc',
            {'A': 1, 'B': 2, 'C': 3},
        ),
    ],
)
def test_pipestring_to_function(pipestring, modules, value, expected):
    assert pype.app._pipestring_to_function(pipestring, modules)(value) == expected


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
        ('? and time.sleep(1)', {'and', 'time.sleep'}),
    ],
)
def test_get_identifiers(string, expected):
    result = pype.app._get_maybe_namespaced_identifiers(string)
    assert result  == expected


def test_cli_raises_without_autoimport(runner):

    args = [
        '--no-autoimport',
        'map',
        'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
    ]
    in_stream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, NameError)



def test_raises_on_missing_module(runner):

    args = [
        'map',
        '_missing_module.replace(?, ".", "!") || collections.Counter || json.dumps ',
    ]
    in_stream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    assert isinstance(result.exception, NameError)


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

    expected = [str(mapper(string))]
    qualname = mapper.__qualname__
    result = list(pype.app.run(qualname, in_stream=[string], newlines=False))

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
    result = list(pype.app.run(qualname, in_stream=[in_stream], newlines=False))

    expected = [str(mapper(in_stream)) ]

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
                'mapper': 'str.upper',
                'newlines': False,
                'in_stream': ['abc'],
            },
            ['ABC'],
        ),
        (
            {
                'mapper': 'str.upper',
                'newlines': True,
                'in_stream': ['abc'],
            },
            ['ABC\n'],
        ),
        (
            {
                'mapper': 'collections.Counter || ?.keys() ',
                'in_stream': ['abbccc\n'],
                'newlines': False,
            },
            [str({'a': 1, 'b': 2, 'c': 3, '\n': 1}.keys())],
        ),
        (
            {
                'mapper': 'collections.Counter || ?.keys() || "".join ',
                'in_stream': ['abbccc\n'],
                'newlines':False,
            },
            ['abc\n'],
        ),
        (
            {
                'mapper': 'collections.Counter || ?.keys() || "".join ',
                'in_stream': [''],
                'newlines': False,
            },
            [''],
        ),
        (
            {
                'mapper': 'str.__add__(?, "bc")',
                'newlines': False,
                'in_stream': ['a'],
            },
            ['abc'],
        ),
        (
            {
                'newlines': False,
                'applier': 'functools.partial(map, str.upper)',
                'in_stream': ['a\nbb\nccc\n'],
            },
            ['A\nBB\nCCC\n'],
        ),
        (

            {
                'newlines': False,
                'applier': '? or time.sleep(1)',
                'in_stream': ['a\nbb\nccc\n'],
            },
            ['a\nbb\nccc\n'],
        ),


    ],
)
def test_main_example(kwargs, expected):
    result = pype.app.run(**kwargs)
    assert list(result) == expected


def test_lambda():
    mapper = 'str.split || sorted(?, key=lambda x: x[-1])'
    in_stream = ['1 2\n2 1\n']
    result = pype.app.run(mapper=mapper, newlines=False, in_stream=in_stream)
    expected = ["['1', '1', '2', '2']"]
    assert list(result) == expected


def test_keyword_arg():
    mapper = 'str.split || sorted(?, key=operator.itemgetter(-1))'
    in_stream = ['1 2\n2 1\n']
    result = pype.app.run(mapper=mapper, newlines=False, in_stream=in_stream)
    expected = ["['1', '1', '2', '2']"]
    assert list(result) == expected


@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize(
    'kwargs, expected',
    [
        (
            {
                'mapper': '"?"',
                'newlines': 'no',
                'in_stream': ['abc'],
            },
            ['"abc"'],
        ),
    ],
)
def test_quoting_error(kwargs, expected):
    result = pype.app.main(**kwargs)
    assert list(result) == expected


@pytest.mark.parametrize(
    'kwargs, expected',
    [
        (
            {
                'mapper': '"?"',
                'newlines': 'no',
                'in_stream': 'abc',
            },
            ['abc'],
        ),
        (
            {
                'mapper': """'I say, "Hello, {?}!"'""",
                'newlines': 'no',
                'in_stream': ['World'],
            },
            ['I say, "Hello, World!"'],
        ),
    ],
)
def test_main_raises_parse_error(kwargs, expected):
    with pytest.raises(PypeParseError):
        list(pype.app.main(**kwargs))


@pytest.mark.xfail(strict=True)
def test_main_f_string():

    result = list(pype.app.main("""f'"{?}"'""", in_stream=['abc'], newlines='no'))
    assert result == ['"abc"']


def test_parse_error():
    with pytest.raises(PypeParseError):
        pype.app._check_parsing('"?"', '?')


@given(string=st.text())
def test_fn_autoimport_counter_keys(string):
    mapper = 'collections.Counter || ?.keys() '
    string = string + '\n'
    in_stream = [string]
    expected = [str(collections.Counter(string).keys()) ]
    result = pype.app.run(mapper=mapper, in_stream=in_stream, newlines=False)
    assert list(result) == expected


@pytest.mark.parametrize(
    'args,expected',
    [
        ((['ab'], 'auto', True), ['ab\n']),
        ((['ab'], 'auto', False), ['ab']),
        ((['ab'], True, True), ['ab\n']),
        ((['ab'], False, True), ['ab']),
        ((['ab'], True, False), ['ab\n']),
        ((['ab\n', 'cd\n'], 'auto', True), ['ab\n', 'cd\n']),
        ((['ab\n', 'cd\n'], True, True), ['ab\n\n', 'cd\n\n']),
        ((['ab\n', 'cd\n'], False, True), ['ab\n', 'cd\n']),
    ],
)
def test_maybe_add_newlines(args, expected):
    text, input_setting, input_has_newlines = args
    assert list(pype.app._maybe_add_newlines(text, input_setting, input_has_newlines)) == expected


@given(string=st.one_of(st.just(''), st.text()))
def test_main_autoimport_placeholder_does_not_raise(string):
    mapper = 'collections.Counter || ?.keys() || "".join '
    pype.app.main(mapper=mapper, in_stream=[string])


@reproduce_failure('3.56.5', b'AAEAIwA=')
@given(string=st.text())
def test_cli_autoimport_placeholder(string, runner):
    args = [
        '--newlines=no',
        'map',
        'str || collections.Counter || ?.keys() || "".join ',
    ]

    in_stream = string

    result = runner.invoke(pype.app.cli, args, input=in_stream)

    expected = ''.join(collections.Counter(in_stream).keys())
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == expected


@pytest.mark.parametrize(
    'args, in_stream, expected',
    [
        (
            ['map', '?'],
            'abc',
            'abc',
        ),
        (
            [
                'map',
                'str.replace(?, ".", "!")',
            ],
            'a.b.c\n',
            'a!b!c\n',
        ),
        (
            [
                '--placeholder=$',
                'map',
                'str.replace($, ".", "!")',
            ],
            'a.b.c\n',
            'a!b!c\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--newlines=no',
                'map',
                'json.dumps(dict(collections.Counter(str.replace(?, ".", "!"))))',
            ],
            'a.b.c',
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--newlines=yes',
                'map',
                'str.replace(?, ".", "!") || collections.Counter(?) || dict(?) || json.dumps(?) ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--newlines=yes',
                'map',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--newlines=yes',
                'map',
                'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
            ],
            'a.b.c\nd.e.f\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n{"d": 1, "!": 2, "e": 1, "f": 1, "\\n": 1}\n',
        ),
        (
            [
                '--newlines=yes',
                'map',
                'str.replace(?, ".", "!") || collections.Counter(?) || json.dumps(?) ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '--newlines=yes',
                'map',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '--newlines=no',
                'map',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c',
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                '--newlines=yes',
                "apply",
                'enumerate || list || reversed || enumerate || list',
            ],
            'a\nbb\nccc\n',
            ("""(0, (2, 'ccc\\n'))
(1, (1, 'bb\\n'))
(2, (0, 'a\\n'))
"""),
        ),
        (
            [
                '--newlines=no',
                "apply",
                'functools.partial(map, str.upper)',
            ],
            'a\nbb\nccc\n',
            'A\nBB\nCCC\n',
        ),
        (
            [
                '--newlines=no',
                'str.replace(?, ".", "!") || collections.Counter || dict || json.dumps ',
            ],
            'a.b.c',
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                '--newlines=no',
                '? or collections.Counter(?)',
            ],
            'a\nbb\nccc\n',
            'a\nbb\nccc\n',
        ),

    ],
)
def test_cli(args, in_stream, expected, runner):

    result = runner.invoke(pype.app.cli, args, input=in_stream)
    assert not result.exception
    assert result.exit_code == 0
    assert result.output == expected

@pytest.mark.parametrize(
    'string, short_placeholder, separator, expected',
    [
        ('?', '?', '||', _PYPE_VALUE + ' '),
        ('1 + ?', '?', '||', f'1 + {_PYPE_VALUE} '),
        ('? + 1', '?', '||', f'{_PYPE_VALUE} +1 '),
    ],
)
def test_replace_short_placeholder(string,short_placeholder, separator,  expected)    :

    result = pype.app._replace_short_placeholder(string, short_placeholder, separator)
    assert result == expected


@pytest.mark.parametrize(
    'string, separator, expected',
    [
        ('a', '||', ['a']),
        ('ab', '||', ['ab']),
        ('ab||cd', '||', ['ab', 'cd']),
        ('ab||cd||ef', '||', ['ab', 'cd', 'ef']),
        ('a"b||c"d||ef', '||', ['a"b||cd', 'ef']),
        ('a', '\\', ['a']),
        ('ab', '\\', ['ab']),
        ('ab\\cd', '\\', ['ab', 'cd']),
        ('ab\\cd\\ef', '\\', ['ab', 'cd', 'ef']),
        ('a"b\\c"d\\ef', '\\', ['a"b\\cd', 'ef']),

    ],
)
def test_split_string_on_separator(string, separator, expected):
    result = pype.app._split_string_on_separator(string, separator)
    assert result == expected


class Timer:
    def __enter__(self):
        self.start = arrow.now()
        return self

    def __exit__(self, *args):
        self.end = arrow.now()
        self.elapsed = self.end - self.start


def test_cli_async(runner, reactor):
    base_url = 'http://localhost:8080/{}'
    letters = string.ascii_lowercase
    in_stream = '\n'.join(base_url.format(c) for c in letters)
    command = 'str.upper || ?.rstrip() || treq.get || treq.text_content '
    args = ['--async', 'map', command]
    expected = [f'Hello, {letter.upper()}' for letter in letters]

    with Timer() as t:
        result = runner.invoke(pype.app.cli, args, input=in_stream)

    lines = result.output.splitlines()
    starts = [line[:8] for line in lines]
    sorted_starts = sorted(starts)

    assert not result.exception
    assert result.exit_code == 0
    assert sorted_starts == expected
    assert t.elapsed < timedelta(seconds=4)


@pytest.mark.xfail(strict=True)
def test_cli_async_chain_map_apply(runner, reactor):
    base_url = 'http://localhost:8080/{}'
    letters = string.ascii_lowercase
    in_stream = '\n'.join(base_url.format(c) for c in letters)
    mapper = 'str.upper || ?.rstrip() || treq.get || treq.text_content '
    applier = 'max'
    args = ['--async', 'map', mapper, 'apply', applier]
    expected = ['Hello, Z']

    with Timer() as t:
        result = runner.invoke(pype.app.cli, args, input=in_stream)

    lines = result.output.splitlines()
    starts = [line[:8] for line in lines]

    assert not result.exception
    assert result.exit_code == 0
    assert len(lines) == 1
    assert starts == expected
    assert t.elapsed < timedelta(seconds=4)

def test_cli_version(runner):
    args = ['--version']

    result = runner.invoke(pype.app.cli, args)

    assert result.output == f'{pype.__name__} {pype._version.__version__}\n'
    assert not result.exception
    assert result.exit_code == 0
