#!/usr/bin/env python


import importlib

import click


def get_modules(imports):
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def make_pipeline(command):
    command_strings = command.split('||')
    pipeline = []
    for string in command_strings:
        if '?' not in string:
            string = string + '(?)'
        stage = string.replace('?', 'value').strip()
        pipeline.append(stage)
    return pipeline


def main(command, in_stream, imports):
    modules = get_modules(imports)
    pipeline = make_pipeline(command)
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
        click.echo(line, nl=False)
