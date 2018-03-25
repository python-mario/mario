#!/usr/bin/env python

"""

$ echo 'a.b.c' | pype 'str.replace(?, ".", "!")'
a!b!c

$ echo 'a.b.c' | pype 'str.replace(?, ".", "!")' | pype -i collections 'dict(collections.Counter(?))'
{a: 1, !: 2, b: 1, c: 1, \n: 1}

"""

import sys
import importlib

import click


def get_modules(imports):
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def main(command, in_stream, imports):
    for line in in_stream:
        out = command.replace('?', 'line')
        modules = get_modules(imports)
        yield eval(out, modules, {'line': line})


@click.command()
@click.option('--import', '-i', 'imports', type=str, multiple=True)
@click.argument('command')
@click.argument('in_stream', default=click.get_text_stream('stdin'))
def cli(imports, command, in_stream):
    gen = main(command, in_stream, imports)
    for line in gen:
        print(line, end='')


if __name__ == '__main__':
    cli()
