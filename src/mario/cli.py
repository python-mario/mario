import os
import sys

import attr
import click


from . import config
from . import utils
from . import _version
from . import app
from . import plug
from . import aliasing

config.DEFAULTS.update(
    config.load_config(
        dir_path=os.environ.get(f"{utils.NAME}_CONFIG_DIR".upper(), None)
    )
)


CONTEXT_SETTINGS = {"default_map": config.DEFAULTS}

doc = f"""\
Mario: Python pipelines for your shell.

GitHub: https://github.com/python-mario/mario

\b
Configuration:
  Declarative config: {config.get_config_dir() / 'config.toml'}
  Python modules: {config.get_config_dir() / 'modules/*.py'}

"""
basics = click.Group(commands=plug.global_registry.cli_functions)
ALIASES = plug.global_registry.aliases


def show(x):
    if hasattr(x, "__dict__"):
        return attr.make_class(type(x).__name__, list(vars(x).keys()))(
            **{k: show(v) for k, v in vars(x).items()}
        )
    if isinstance(x, list):
        return [show(v) for v in x]
    if isinstance(x, dict):
        return {k: show(v) for k, v in x.items()}
    return repr(x)


def cli_main(pairs, **kwargs):
    app.main(pairs, **kwargs)


def version_option(ctx, param, value):
    if not value:
        return
    click.echo("mario, version " + _version.__version__)
    sys.exit()


def build_stages(alias):
    def run(ctx, **cli_params):
        out = []
        for stage in alias.stages:

            mapped_stage_params = {
                remap.old.lstrip("-"): cli_params[remap.new.lstrip("-")]
                for remap in stage.remap_params
            }
            mapped_stage_params.update(stage.options)
            inject_namespace = {
                k: v for k, v in cli_params.items() if k in alias.inject_values
            }
            cmd = cli.get_command(ctx, stage.command)
            out.extend(
                ctx.invoke(cmd, **mapped_stage_params, inject_values=inject_namespace)
            )
        return out

    params = alias.arguments + alias.options
    return click.Command(
        name=alias.name, params=params, callback=click.pass_context(run)
    )


COMMANDS = plug.global_registry.cli_functions
for k, v in ALIASES.items():
    COMMANDS[k] = build_stages(v)


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
    commands=COMMANDS,
)
