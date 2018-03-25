#!/usr/bin/env python

"""

$ echo 'a.b.c' | pype.py 'str.replace(?, ".", "!")'
a!b!c

"""

import sys

import click


def parse_command(command):
    fnstr = 'lambda placeholder: ' + command.replace('?', 'placeholder')
    return eval(fnstr)


def main(in_stream, command):
    process = parse_command(command)
    for line in in_stream:
        yield process(line)


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
