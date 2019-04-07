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
@click.option('--autocall/--no-autocall', is_flag=True, default=config.DEFAULTS['autocall'])
@click.version_option(_version.__version__, prog_name="pype")
def cli(**kwargs):
    pass


def make_subcommand(name):
    @click.command(name)
    @click.argument("command")
    def _subcommand(command):
        return (name, command)

    return _subcommand


subcommand_names = ["map", "apply", "filter", "eval", "stack"]
subcommands = [make_subcommand(name) for name in subcommand_names]
for subcommand in subcommands:
    cli.add_command(subcommand)


@cli.resultcallback()
def cli_main(pairs, **kwargs):
    app.main(pairs, **kwargs)
