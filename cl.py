#!/usr/bin/env python3

import click


@click.group(chain=True)
def cli():
    pass


@cli.command()
def greet():
    print("hello")


@cli.group()
def read():
    pass


@cli.group()
def write():
    pass


@read.command()
@click.option("--header/--no-header")
def csv(header):
    print("reading csv")


@write.command()
def json():
    print("writing json")


if __name__ == "__main__":
    cli()


# With chain=False,
# cl.py read csv write json
# Usage: cl.py read csv [OPTIONS]
# Try "cl.py read csv --help" for help.

# Error: Got unexpected extra arguments (write json)


# With chain=True,
# cl.py read csv write json
# Traceback (most recent call last):
#   File "cl.py", line 16, in <module>
#     @cli.group()
#  ...
# RuntimeError: It is not possible to add multi commands as children to another multi command that is in chain mode.  Command "cli" is set to chain and "read" was added as subcommand but it in itself is a multi command.  ("read" is a Group within a chained Group named "cli")
