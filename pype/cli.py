import os

import click

from . import config
from . import utils
from . import _version
from . import app
from . import plug


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


def synth_to_click(syn):



    callback = lambda: {'command': syn.prepend[0].body, 'name': syn.prepend[0].traversal_name}
    return click.Command(
        syn.name,
        callback=callback,
        short_help=syn.short_help,
    )


for subcommand_name, subcommand in plug.global_registry.cli_functions.items():
    cli.add_command(subcommand, name=subcommand_name)


for synth_name, synth in plug.global_registry.synthetic_commands.items():
    cli.add_command(synth_to_click(synth), name=synth_name)


@cli.resultcallback()
def cli_main(pairs, **kwargs):
    app.main(pairs, **kwargs)
