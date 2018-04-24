#!/usr/bin/env python

from __future__ import generator_stop

from pdb import set_trace as st

import importlib
import itertools
import os
import re
import sys
import token
import io
from tokenize import tokenize, untokenize

import attr
import click
import toolz

_PYPE_VALUE = '__PYPE_VALUE_'


def _is_name_token(token_object):
    return token.tok_name[token_object.type] == 'NAME'


def _is_reference_part(token_object):
    if _is_name_token(token_object):
        return True
    if token_object.string == '.':
        return True
    return False


def _string_to_tokens(string):
    bytestring = string.encode('utf-8')
    bytesio = io.BytesIO(bytestring)
    tokens = tokenize(bytesio.readline)
    return tokens


def _tokens_to_string(token_objects):
    """Untokenize, ignoring whitespace."""
    return ''.join(t.string for t in token_objects)


def _get_identifiers(string):
    scanner = _StringScanner(string)
    return scanner.scan()


@attr.s
class _StringScanner:

    _string = attr.ib()
    _current_tokens = attr.ib(default=attr.Factory(list))
    _identifier_strings = attr.ib(default=attr.Factory(set))

    def _maybe_update(self):
        if self._current_tokens and _is_name_token(self._current_tokens[-1]):
            if _is_name_token(self._current_tokens[0]):
                self._identifier_strings.add(_tokens_to_string(self._current_tokens))
            self._current_tokens = []

    def scan(self):
        tokens = _string_to_tokens(self._string)

        for token_object in tokens:

            if _is_reference_part(token_object):
                self._current_tokens.append(token_object)
                continue

            self._maybe_update()

        self._maybe_update()

        return self._identifier_strings


def _get_named_module(name):
    builtins = sys.modules['builtins']
    if hasattr(builtins, name):
        return builtins
    try:
        return importlib.import_module(name)
    except ImportError:
        pass
    raise LookupError(f'Could not find {name}')


def _get_autoimport_modules(fullname):
    name_parts = fullname.split('.')
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, '.'.join(name_parts[:idx + 1]))

    for name in try_names:
        try:
            module = _get_named_module(name)
        except LookupError:
            pass
        else:
            if module is sys.modules['builtins']:
                return {}
            return {name: module}
    raise RuntimeError(f'Could not find {fullname}')


def _get_named_modules(imports):
    """Import modules into dict mapping name to module."""
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def _make_pipeline_strings(command, placeholder, star_args=False):
    """Parse pipeline into individual components."""
    command_strings = command.split('||')
    pipeline = []
    for string in command_strings:
        string = string.strip()
        if placeholder not in string:
            string = string + '({star}{placeholder})'.format(
                star='*' if star_args else '', placeholder=placeholder)
        stage = string.replace(placeholder, _PYPE_VALUE).strip()
        pipeline.append(stage)
    return pipeline


def _get_autoimports(string):
    components = [comp.strip() for comp in string.split('||')]
    name_to_module = {}
    for component in components:
        identifiers = _get_identifiers(component)
        for identifier in identifiers:
            name_module = _get_autoimport_modules(identifier)
            name_to_module.update(name_module)
    return name_to_module


def _get_modules(commands, named_imports, autoimport):
    named_modules = _get_named_modules(named_imports)
    if not autoimport:
        return named_modules
    autoimports = toolz.merge(_get_autoimports(command) for command in commands)
    # named modules have priority
    modules = {**autoimports, **named_modules}
    return modules


def _apply_command_pipeline(value, modules, pipeline):
    assert modules is not None
    for step in pipeline:
        value = eval(step, modules, {_PYPE_VALUE: value})
    return value


def _apply_total(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    string = in_stream.read()
    result = _apply_command_pipeline(string, modules, pipeline)
    yield result


def _apply_map(command, in_stream, imports, placeholder, autoimport):
    import itertools
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    for line in in_stream:
        result = _apply_command_pipeline(line, modules, pipeline)
        yield result


def _apply_reduce(command, in_stream, imports, placeholder, autoimport):

    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder, star_args=True)

    value = next(in_stream)
    for item in in_stream:
        for step in pipeline:
            value = eval(step, modules, {_PYPE_VALUE: (value, item)})
    yield value


def _maybe_add_newlines(iterator, newlines_setting='auto'):

    if newlines_setting == 'auto':
        try:
            first, iterator = toolz.peek(iterator)
        except StopIteration:
            add_newlines = False
        else:
            add_newlines = not str(first).endswith('\n')

    else:
        add_newlines = {'yes': True, 'no': False}[newlines_setting]

    for item in iterator:
        string = str(item)
        if add_newlines:
            yield string + os.linesep
        else:
            yield string


def main(  # pylint: disable=too-many-arguments
        mapper,
        reducer=None,
        postmap=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        slurp=False,
        autoimport=True,
        newlines='auto',
):

    if slurp:
        result = _apply_total(mapper, in_stream, imports, placeholder, autoimport)
    else:
        result = _apply_map(mapper, in_stream, imports, placeholder, autoimport)

    if reducer is not None:
        result = _apply_reduce(reducer, result, imports, placeholder, autoimport)
    if postmap is not None:
        result = _apply_map(postmap, result, imports, placeholder, autoimport)

    result = _maybe_add_newlines(result, newlines)

    yield from result


@click.command()
@click.argument('command')
@click.argument('reducer', default=None, required=False)
@click.argument('postmap', default=None, required=False)
@click.option(
    '--slurp',
    '-s',
    is_flag=True,
    help='Apply function to entire input together instead of processing one line at a time.')
@click.option(
    '--newlines',
    '-n',
    type=click.Choice(['auto', 'yes', 'no']),
    default='auto',
    help='Add newlines.')
@click.option(
    '--autoimport/--no-autoimport',
    is_flag=True,
    default=True,
    help='Automatically import modules.')
@click.option(
    '--import',
    '-i',
    'imports',
    multiple=True,
    help='Modules to import explicitly.',
)
@click.option(
    '--placeholder',
    default='?',
    help='String to replace with data. Defaults to ?',
)
def cli(
        imports,
        command,
        reducer,
        placeholder,
        slurp,
        postmap,
        autoimport,
        newlines,
):
    """
Pipe data through python functions.

\b
$ printf 'a.b.c\\nd.e.f\\n' |
pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || json.dumps '

\b
{"A": 1, "!": 2, "B": 1, "C": 1, "\\n": 1}
{"D": 1, "!": 2, "E": 1, "F": 1, "\\n": 1}

\b
$ printf 'aa.bbb\\n' | pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || {v:k for k,v in ?.items()} || json.dumps'

\b
{"2": "A", "1": "\\n", "3": "B"}

\b
$ printf 'a\\nab\\nabc\\n' | pype -i json -i toolz -i collections 'collections.Counter' 'toolz.merge_with(sum, ?)' 'json.dumps'

\b
{"a": 3, "\\n": 3, "b": 2, "c": 1}

\b
$ printf 'a\\nab\\nabc\\n' | pype -t -i json -i toolz -i collections 'collections.Counter || json.dumps'

\b
{"a": 3, "\\n": 3, "b": 2, "c": 1}


    """
    in_stream = click.get_text_stream('stdin')
    gen = main(command, reducer, postmap, in_stream, imports, placeholder, slurp, autoimport,
               newlines)

    for line in gen:
        click.echo(line, nl=False)
