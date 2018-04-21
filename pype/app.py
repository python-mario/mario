#!/usr/bin/env python

import functools
import importlib
from pprint import pprint as pp

import click


def identity(x):
    "Identity function."
    return x


def get_modules(imports):
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
        stage = string.replace(placeholder, 'value').strip()
        pipeline.append(stage)
    return pipeline


def apply_command_pipeline(value, modules, pipeline):
    for step in pipeline:
        value = eval(step, modules, {'value': value})
    return value


def apply_total(command, in_stream, imports, placeholder):
    modules = get_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder)
    string = in_stream.read()
    result = apply_command_pipeline(string, modules, pipeline)
    yield result


def apply_map(command, in_stream, imports, placeholder):

    modules = get_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder)
    for line in in_stream:
        yield apply_command_pipeline(line, modules, pipeline)


def apply_reduce(command, in_stream, imports, placeholder):

    modules = get_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder, star_args=True)

    value = next(in_stream)
    for item in in_stream:
        for step in pipeline:
            value = eval(step, modules, {'value': (value, item)})
    yield value


def main(mapper, reducer, in_stream, imports, placeholder, total):
    if total:
        yield from apply_total(mapper, in_stream, imports, placeholder)

    if reducer is None:
        reducer = placeholder
    mapped = apply_map(mapper, in_stream, imports, placeholder)
    reduced = apply_reduce(reducer, mapped, imports, placeholder)
    yield from reduced


@click.command()
@click.option(
    '--import', '-i', 'imports', type=str, multiple=True,
    help='Modules to import',
)
@click.option(
    '--placeholder', '-p', type=str, default='?',
    help='String to replace with data. Defaults to ?',
)
@click.argument('command', type=str)
@click.argument('reducer', type=str, default=None, required=False,
                )
@click.argument(
    'in_stream', default=click.get_text_stream('stdin'), required=False
)
@click.option('--total', '-t', is_flag=True, help='Apply function to entire input together.')
def cli(imports, command, reducer, in_stream, placeholder, total):
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


    """
    gen = main(command, reducer, in_stream, imports, placeholder, total)
    for line in gen:
        click.echo(line, nl=True)
    click.echo()
