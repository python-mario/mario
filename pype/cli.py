import os

import click

from . import config
from . import utils
from . import _version
from . import app


config.DEFAULTS.update(
    config.load_config(
        dir_path=os.environ.get(f"{utils.NAME}_CONFIG_DIR".upper(), None)
    )
)
CONTEXT_SETTINGS = {"default_map": config.DEFAULTS}


@click.group(chain=True, context_settings=CONTEXT_SETTINGS)
@click.option("--max-concurrent", type=int, default=config.DEFAULTS["max_concurrent"])
@click.option(
    "--exec-before",
    help="Python source code to be executed before any stage.",
    default=config.DEFAULTS["exec_before"],
)
@click.option(
    "--autocall/--no-autocall", is_flag=True, default=config.DEFAULTS["autocall"]
)
@click.version_option(_version.__version__, prog_name="pype")
def cli(**kwargs):
    pass


subcommands = [
    click.Command("map", short_help="Call <command> on each line of input."),
    click.Command("apply", short_help="Call <command> on input as a sequence."),
    click.Command(
        "filter",
        short_help="Call <command> on each line of input and exclude false values.",
    ),
    click.Command("eval", short_help="Call <command> without any input."),
    click.Command(
        "stack", short_help="Call <command> on input as a single concatenated string."
    ),
]


def build_callback(sub_command):
    def callback(command):
        return sub_command.name, command

    return callback


for subcommand in subcommands:
    subcommand.params = [click.Argument(["command"])]
    subcommand.callback = build_callback(subcommand)
    cli.add_command(subcommand)

@cli.resultcallback()
def cli_main(pairs, **kwargs):
    app.main(pairs, **kwargs)
