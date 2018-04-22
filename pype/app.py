#!/usr/bin/env python


from __future__ import generator_stop

from pdb import set_trace as st

import importlib
import re
import sys


import click
import toolz


_PYPE_VALUE = '__PYPE_VALUE_'


def _get_identifiers(string):
    identifier_pattern = r'[^\d\W]\w*'
    namespaced_identifier_pattern = r'\b{id}(?:\.{id})*'.format(
        id=identifier_pattern
    )
    matches = re.findall(
        namespaced_identifier_pattern, string.strip(), re.UNICODE
    )
    return set(matches)


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
                star='*' if star_args else '', placeholder=placeholder
            )
        stage = string.replace(placeholder, f'{_PYPE_VALUE}').strip()
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
    autoimports = toolz.merge(_get_autoimports(command)
                              for command in commands)
    # named modules have priority
    modules = {**autoimports, **named_modules}
    return modules


def _apply_command_pipeline(value, modules, pipeline):
    assert modules is not None
    for step in pipeline:
        value = eval(step, modules, {f'{_PYPE_VALUE}': value})
    return value


def _apply_total(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    string = in_stream.read()
    result = _apply_command_pipeline(string, modules, pipeline)
    yield result


def _apply_map(command, in_stream, imports, placeholder, autoimport):
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
            value = eval(step, modules, {f'{_PYPE_VALUE}': (value, item)})
    yield value


def main(mapper, reducer=None, postmap=None, in_stream=None, imports=(), placeholder='?', total=False, autoimport=True):
    if total:
        yield from _apply_total(mapper, in_stream, imports, placeholder, autoimport)
        return
    mapped = _apply_map(mapper, in_stream, imports, placeholder, autoimport)
    if reducer is None:
        yield from mapped
        return
    reduced = _apply_reduce(reducer, mapped, imports, placeholder, autoimport)
    if postmap is None:
        yield from reduced
        return
    yield from _apply_map(postmap, reduced, imports, placeholder, autoimport)
    return


@click.command()
@click.argument('command')
@click.argument('reducer', default=None, required=False)
@click.argument('postmap', default=None, required=False)
@click.option(
    '--total',
    '-t',
    is_flag=True,
    help='Apply function to entire input together.'
)
@click.option(
    '--newlines',
    '-n',
    type=click.Choice(['auto', 'yes', 'no']),
    default='auto', help='Add newlines.'
)
@click.option(
    '--autoimport/--no-autoimport',
    is_flag=True,
    default=True,
    help='Automatically import modules.'
)
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
        imports, command, reducer, placeholder,
        total, postmap, autoimport, newlines,
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
    gen = main(command, reducer, postmap, in_stream,
               imports, placeholder, total, autoimport)

    if newlines == 'auto':
        first, gen = toolz.peek(gen)
        add_newlines = not str(first).endswith('\n')
    else:
        add_newlines = {'yes': True, 'no': False}[newlines]

    for line in gen:
        click.echo(line, nl=add_newlines)
