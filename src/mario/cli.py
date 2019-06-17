import os
import sys

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

doc = """Mario: Python pipelines for your shell.

    GitHub: https://github.com/python-mario/mario

    """


# click.version_option(_version.__version__, prog_name="mario")

# import pp
def cli_main(pairs, **kwargs):
    # pp({'pairs': pairs, 'kwargs':kwargs})
    app.main(pairs, **kwargs)


def version_option(ctx, param, value):
    if not value:
        return
    click.echo("mario, version " + _version.__version__)
    sys.exit()


cli = click.Group(
    result_callback=cli_main,
    chain=True,
    context_settings=CONTEXT_SETTINGS,
    params=[
        click.Option(
            ["--max-concurrent"], type=int, default=config.DEFAULTS["max_concurrent"]
        ),
        click.Option(
            ["--exec-before"],
            help="Python source code to be executed before any stage.",
            default=config.DEFAULTS["exec_before"],
        ),
        click.Option(
            ["--base-exec-before"],
            help="Python source code to be executed before any stage; typically set in the user config file. Combined with --exec-before value. ",
            default=config.DEFAULTS["base_exec_before"],
        ),
        click.Option(
            ["--version"],
            callback=version_option,
            is_flag=True,
            help="Show the version and exit.",
        ),
    ],
    help=doc,
    commands=plug.global_registry.cli_functions,
)


def _make_callback(alias):
    return [
        {
            "name": component.name,
            "pipeline": component.arguments[0] if component.arguments else None,
            "parameters": component.options,
        }
        for component in alias.components
    ]


def alias_to_click(alias):
    print(alias)

    params = []

    return click.Command(
        alias.name, callback=cli.callback, params=params, short_help=alias.short_help
    )


for alias_name, alias in plug.global_registry.aliases.items():
    cli.add_command(alias_to_click(alias), name=alias_name)
