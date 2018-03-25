#!/usr/bin/env python

"""

$ echo 'a.b.c' | pype 'str.replace(?, ".", "!")'
a!b!c

$ echo 'a.b.c' | pype 'str.replace(?, ".", "!")' | pype -i collections 'dict(collections.Counter(?))'
{a: 1, !: 2, b: 1, c: 1, \n: 1}

"""

import importlib

import click


def get_modules(imports):
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def main(command, in_stream, imports):
    modules = get_modules(imports)
    pipeline = command.replace('?', 'value').split('||')
    for line in in_stream:
        value = line
        for step in pipeline:
            value = eval(step, modules, {'value': value})
        yield value


@click.command()
@click.option('--import', '-i', 'imports', type=str, multiple=True)
@click.argument('command')
@click.argument('in_stream', default=click.get_text_stream('stdin'), required=False)
def cli(imports, command, in_stream):
    gen = main(command, in_stream, imports)
    for line in gen:
        click.echo(line)
