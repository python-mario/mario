#!/usr/bin/env python

"""

$ echo 'a.b.c' | python pype -i 'collections' -- 'collections.Counter(str.replace(?, ".", "!"))'
Counter({'!': 2, 'a': 1, 'b': 1, 'c': 1, '\n': 1})

$ echo 'a.b.c' | python pype 'str.replace(?, ".", "!")' | python pype -i collections 'collections.Counter(?)'
Counter({'!': 2, 'a': 1, 'b': 1, 'c': 1, '\n': 1})
Counter({'\n': 1})

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
        print(line)


if __name__ == '__main__':
    cli()
