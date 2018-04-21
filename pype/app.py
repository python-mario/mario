#!/usr/bin/env python

# TODO Consider what happens with quoting when using autoimport.
# TODO Prefix private functions with _.

from __future__ import generator_stop

from pdb import set_trace as st
from pprint import pprint as pp
import collections
import functools
import importlib
import importlib
import json
import re
import sys


import click
import toolz


def get_identifiers(string):
    identifier_pattern = r'[^\d\W]\w*'
    namespaced_identifier_pattern = r'\b{id}(?:\.{id})*'.format(
        id=identifier_pattern
    )
    matches = re.findall(
        namespaced_identifier_pattern, string.strip(), re.UNICODE
    )
    return set(matches)


BUILTIN = object()


def get_named_module(name):
    builtins = sys.modules['builtins']
    if hasattr(builtins, name):
        return builtins
    try:
        return importlib.import_module(name)
    except ImportError:
        pass
    raise LookupError(f'Could not find {name}')


def get_autoimport_modules(fullname):
    name_parts = fullname.split('.')
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, '.'.join(name_parts[:idx + 1]))

    for name in try_names:
        try:
            module = get_named_module(name)
        except LookupError:
            pass
        else:
            if module is sys.modules['builtins']:
                return {}
            return {name: module}
    raise RuntimeError(f'Could not find {fullname}')


def get_named_modules(imports):
    """Import modules into dict mapping name to module."""
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def make_pipeline_strings(command, placeholder, star_args=False):
    """Parse pipeline into individual components."""
    command_strings = command.split('||')
    pipeline = []
    for string in command_strings:
        string = string.strip()
        if placeholder not in string:
            string = string + '({star}{placeholder})'.format(
                star='*' if star_args else '', placeholder=placeholder
            )
        stage = string.replace(placeholder, '_pype_value_').strip()
        pipeline.append(stage)
    return pipeline


def apply_command_pipeline(value, modules, pipeline):
    assert modules is not None
    for step in pipeline:
        value = eval(step, modules, {'_pype_value_': value})
    return value


def apply_total(command, in_stream, imports, placeholder):
    modules = get_named_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder)
    string = in_stream.read()
    result = apply_command_pipeline(string, modules, pipeline)
    yield result


def get_autoimports(string):
    components = [comp.strip() for comp in string.split('||')]
    name_to_module = {}
    for component in components:
        identifiers = get_identifiers(component)
        for identifier in identifiers:
            name_module = get_autoimport_modules(identifier)
            name_to_module.update(name_module)
    return name_to_module


def get_modules(commands, named_imports):
    named_modules = get_named_modules(named_imports)
    autoimports = toolz.merge(get_autoimports(command) for command in commands)
    autoimport_modules = {k: v for k, v in autoimports.items()}
    # named modules have priority
    modules = {**autoimports, **named_modules}
    return modules


def apply_map(command, in_stream, imports, placeholder):
    modules = get_modules([command], imports)
    pipeline = make_pipeline_strings(command, placeholder)
    for line in in_stream:
        result = apply_command_pipeline(line, modules, pipeline)
        yield result


def apply_reduce(command, in_stream, imports, placeholder):

    modules = get_named_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder, star_args=True)

    value = next(in_stream)
    for item in in_stream:
        for step in pipeline:
            value = eval(step, modules, {'_pype_value_': (value, item)})
    yield value


def main(mapper, reducer, postmap, in_stream, imports, placeholder, total):
    if total:
        yield from apply_total(mapper, in_stream, imports, placeholder)
        return
    mapped = apply_map(mapper, in_stream, imports, placeholder)
    if reducer is None:
        yield from mapped
        return
    reduced = apply_reduce(reducer, mapped, imports, placeholder)
    if postmap is None:
        yield from reduced
        return
    yield from apply_map(postmap, reduced, imports, placeholder)
    return


@click.command()
@click.option('--autoimport', '-a', is_flag=True)
@click.option(
    '--import', '-i', 'imports', type=str, multiple=True,
    help='Modules to import',


)
@click.option(
    '--placeholder', '-p', type=str, default='?',
    help='String to replace with data. Defaults to ?',
)
@click.argument('command', type=str)
@click.argument('reducer', type=str, default=None, required=False,)
@click.argument('postmap', default=None, required=False)
@click.argument(
    'in_stream', default=click.get_text_stream('stdin'), required=False
)
@click.option('--total', '-t', is_flag=True, help='Apply function to entire input together.')
def cli(imports, command, reducer, in_stream, placeholder, total, postmap, autoimport):
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
    gen = main(command, reducer, postmap, in_stream,
               imports, placeholder, total)
    for line in gen:
        click.echo(line, nl=True)
    click.echo()
