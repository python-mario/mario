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


@pytest.mark.parametrize(
    'args,  expected',
    [
        (['str.replace(?, ".", "!")', '?', '?', ('a.b.c\n',)], 'a!b!c\n'),
        (['-p$', 'str.replace($, ".", "!")', '$', '$', ('a.b.c\n',)], 'a!b!c\n'),
        (
            [
                '-icollections',
                '-ijson',
                'json.dumps(dict(collections.Counter(str.replace(?, ".", "!"))))',
                '?',
                '?',
                ('a.b.c',),
            ],
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                '-icollections',
                '-ijson',
                'str.replace(?, ".", "!") '
                '|| collections.Counter(?) '
                '|| dict(?) '
                '|| json.dumps(?) ',
                '?',
                '?',
                ('a.b.c',),
            ],
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                '-icollections',
                '-ijson',
                'str.replace(?, ".", "!") '
                '|| collections.Counter '
                '|| dict '
                '|| json.dumps ',
                '?',
                '?',
                ('a.b.c',),
            ],
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
        (
            [
                "-i", "toolz",
                "-i", "collections",
                ' str.replace(?, ".", "!") || collections.Counter',
                'toolz.merge_with(sum, ?)',
                '?',
                ("a.b.c\n", "d.e.f\n",),
            ],
            r"{'a': 1, '!': 4, 'b': 1, 'c': 1, "
            r"'\n': 2, 'd': 1, 'e': 1, 'f': 1}",
        ),
        (
            [
                '-a ',
                'str.replace(?, ".", "!") '
                '|| collections.Counter(?) '
                '|| dict(?) '
                '|| json.dumps(?) ',
                '?',
                '?',
                ('a.b.c',),
            ],
            '{"a": 1, "!": 2, "b": 1, "c": 1}',
        ),
    ],
)
def test_cli(args, expected):

    runner = CliRunner()
    result = runner.invoke(pype.app.cli, args)
    assert not result.exception
    assert result.output.strip() == expected.strip()


@pytest.mark.parametrize(
    'command, expected',
    [
        ('str.upper(?)', ['str.upper(_pype_value_)']),
        ('str.upper', ['str.upper(_pype_value_)']),
        (
            'str.upper(?) || "X".join',
            [
                'str.upper(_pype_value_)', '"X".join(_pype_value_)'
            ]),
    ]
)
def test_make_pipeline(command, expected):
    assert pype.app.make_pipeline_strings(command, '?') == expected


@pytest.mark.parametrize(
    'name, expected',
    [

        ('str.upper', str.upper),
        ('os.path.join', os.path.join),
        ('map', map),
        ('collections.Counter', collections.Counter),
        ('urllib.parse.urlparse', urllib.parse.urlparse),
    ],
)
def test_get_function(name, expected):
    assert pype.app.get_function(name) == expected


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
    assert pype.app.get_identifiers(string) == expected
