#!/usr/bin/env python3

import attr
import click


class SectionedHelpCommand(click.Command):
    """Sections commands into help groups"""

    def command(self, *args, **kwargs):
        help_group = kwargs.pop("help_group")
        decorator = super().command(*args, **kwargs)

        def new_decorator(f):
            cmd = decorator(f)
            cmd.help_group = help_group
            self.grouped_commands.setdefault(help_group, []).append(cmd)
            return cmd

        return new_decorator

    def format_options(self, ctx, formatter):
        grouped_commands = {}
        for param in self.params:
            if hasattr(param, "for_command"):
                grouped_commands.setdefault(param.for_command, []).append(param.name)

        for group, cmds in grouped_commands.items():
            rows = []
            [choice_argument] = [
                param
                for param in self.params
                if isinstance(param, click.Argument)
                and isinstance(param.type, click.Choice)
            ]
            subcommand_name = ctx.params[choice_argument.name]
            for param in self.params:

                if param.name in [choice_argument.name, "help"]:
                    continue
                if not param.name in grouped_commands[subcommand_name]:
                    continue
                rows.append(param.get_help_record(ctx))

            if rows:
                with formatter.section(group):
                    formatter.write_dl(rows)


@click.group(chain=True, add_help_option=False)
def cli():
    pass


@cli.command()
@click.argument("arg", type=click.Choice([int, float]))
def greet(arg):
    print("hello")


def read_callback(ctx, **kwargs):
    if kwargs["help"]:

        print(read.get_help(ctx))
        return

    print("read", kwargs)


class OptionForCommand(click.Option):
    def __init__(self, *args, for_command, **kwargs):
        self.for_command = for_command
        super().__init__(*args, **kwargs)


read = SectionedHelpCommand(
    "read",
    callback=click.pass_context(read_callback),
    params=[
        click.Argument(["format"], type=click.Choice(["json", "csv"])),
        click.Option(["--help"], is_flag=True, type=bool),
        OptionForCommand(
            ["--header/--no-header"], help="Is there a header?", for_command="csv"
        ),
        OptionForCommand(
            ["--some-json-option"], help="Something about json", for_command="json"
        ),
    ],
    add_help_option=False,
)

cli.add_command(read)


@cli.command(add_help_option=False)
@click.argument("format")
def write(format):
    print("write", format)


if __name__ == "__main__":
    cli()
