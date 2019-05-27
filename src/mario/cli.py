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
    "--base-exec-before",
    help="Python source code to be executed before any stage; typically set in the user config file. Combined with --exec-before value. ",
    default=config.DEFAULTS["base_exec_before"],
)
@click.version_option(_version.__version__, prog_name="mario")
def cli(**kwargs):
    """Mario: Python pipelines for your shell.

    GitHub: https://github.com/python-mario/mario

    """
    pass


def alias_to_click(alias):

    callback = lambda: [
        {
            "name": component.name,
            "pipeline": component.arguments[0] if component.arguments else None,
            "parameters": component.options,
        }
        for component in alias.components
    ]
    return click.Command(alias.name, callback=callback, short_help=alias.short_help)


for subcommand_name, subcommand in plug.global_registry.cli_functions.items():
    cli.add_command(subcommand, name=subcommand_name)


for alias_name, alias in plug.global_registry.aliases.items():
    cli.add_command(alias_to_click(alias), name=alias_name)


@cli.resultcallback()
def cli_main(pairs, **kwargs):
    app.main(pairs, **kwargs)
