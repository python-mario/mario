#!/usr/bin/env python

"""

$ echo 'a.b.c' | pype 'str.replace(?, ".", "!")'
a!b!c

"""

import sys

import click


def main(in_stream, command):
    for line in in_stream:
        out = command.replace('?', 'line')
        yield eval(out)


@click.command()
@click.option('--import', '-i', 'import_')
@click.argument('command')
@click.argument('in_stream', default=click.get_text_stream('stdin'))
def cli(import_, command, in_stream):

    gen = main(in_stream, command)
    for line in gen:
        print(line)


if __name__ == '__main__':
    cli()
