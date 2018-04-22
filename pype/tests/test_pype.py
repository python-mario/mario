import collections
import os
import urllib

import pytest
from click.testing import CliRunner
from hypothesis import given
from hypothesis.strategies import text
import toolz

import pype
import pype.app
from pype.app import _PYPE_VALUE


@pytest.fixture(name='runner')
def _runner():
    return CliRunner()


@pytest.mark.parametrize(
    'args, input, expected',
    [
        (['str.replace(?, ".", "!")', '?', '?', ], 'a.b.c\n', 'a!b!c\n'),
        (['-p$', 'str.replace($, ".", "!")', '$', '$', ], 'a.b.c\n', 'a!b!c\n'),
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
            ['str.replace(?, ".", "!") || collections.Counter(?) || json.dumps(?) ', ],
            'a.b.c\n',
            '{"a": 1, "!": 2, "b": 1, "c": 1, "\\n": 1}\n',
        ),
        (
            [
                '-icollections',
                '-ijson',
                '--total',
                'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
            ],
            'a.b.c\nd.e.f\n',
            '{"a": 1, "!": 4, "b": 1, "c": 1, "\\n": 2, "d": 1, "e": 1, "f": 1}\n',

        ),
    ],
)
def test_cli(args, input, expected, runner):

    result = runner.invoke(pype.app.cli, args, input=input)
    assert not result.exception
    assert result.output == expected


@pytest.mark.parametrize(
    'command, expected',
    [
        ('str.upper(?)', [f'str.upper({_PYPE_VALUE})']),
        ('str.upper', [f'str.upper({_PYPE_VALUE})']),
        (
            'str.upper(?) || "X".join',
            [
                f'str.upper({_PYPE_VALUE})', f'"X".join({_PYPE_VALUE})'
            ]
        ),
    ]
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
        ('map', {'map'}),
        ('map(json.dumps)', {'map', 'json.dumps'}),
        ('collections.Counter(?)', {'collections.Counter'}),
        ('urllib.parse.urlparse', {'urllib.parse.urlparse'}),
        ('1 + 2', set()),
        (
            'json.dumps(collections.Counter)',
            {'json.dumps', 'collections.Counter'}
        )
    ],
)
def test_get_identifiers(string, expected):
    assert pype.app._get_identifiers(string) == expected


def test_cli_raises_without_autoimport(runner):

    args = [
        '--no-autoimport',
        'str.replace(?, ".", "!") || collections.Counter || json.dumps ',
    ]
    instream = 'a.b.c\n'

    result = runner.invoke(pype.app.cli, args, input=instream)
    assert isinstance(result.exception, NameError)
