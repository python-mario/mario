#!/usr/bin/env python


import importlib

import click
from pdb import set_trace as st


def get_modules(imports):
    """Import modules into dict mapping name to module."""
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def make_pipeline_strings(command, placeholder='?'):
    """Parse pipeline into individual components."""
    command_strings = command.split('||')
    pipeline = []
    for string in command_strings:
        string = string.strip()
        if placeholder not in string:
            string = string + '({placeholder})'.format(placeholder=placeholder)
        stage = string.replace(placeholder, 'value').strip()
        pipeline.append(stage)
    return pipeline


def main(command, in_stream, imports, placeholder):
    modules = get_modules(imports)
    pipeline = make_pipeline_strings(command, placeholder)
    for line in in_stream:
        value = line
        for step in pipeline:
            value = eval(step, modules, {'value': value})
        yield value


@click.command()
@click.option('--import', '-i', 'imports', type=str, multiple=True, help='Modules to import')
@click.option('--placeholder', '-p', type=str, default='?', help='String to replace with data. Defaults to ?')
@click.argument('command', type=str)
@click.argument('in_stream', default=click.get_text_stream('stdin'), required=False)
def cli(imports, command, in_stream, placeholder):
    """
Pipe data through python functions.

\b
$ printf 'a.b.c\\nd.e.f\\n' |
pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || dict || json.dumps '

\b
{"A": 1, "!": 2, "B": 1, "C": 1, "\\n": 1}
{"D": 1, "!": 2, "E": 1, "F": 1, "\\n": 1}

\b
$ printf 'aa.bbb\\n' | pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || {v:k for k,v in ?.items()} || json.dumps'

\b
{"2": "A", "1": "\\n", "3": "B"}


    """
    gen = main(command, in_stream, imports, placeholder)
    for line in gen:
        click.echo(line, nl=True)
    click.echo()
