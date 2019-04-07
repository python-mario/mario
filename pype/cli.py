import os

import click

from . import config
from . import utils
from . import _version
from . import app


config.DEFAULTS.update(config.load_config(os.environ.get(f"{utils.NAME}_CONFIG_DIR", None)))
CONTEXT_SETTINGS = {"default_map": config.DEFAULTS}



@click.group(chain=True, context_settings=CONTEXT_SETTINGS)
@click.option("--max-concurrent", type=int, default=config.DEFAULTS["max_concurrent"])
@click.option(
    "--exec-before",
    help="Python source code to be executed before any stage.",
    default=config.DEFAULTS["exec_before"],
)
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


# time python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map 'len(x)' filter 'x < 195' apply 'len(x)' <<EOF
# http://httpbin.org/delay/3
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# EOF
# 8
# python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map   0.45s user 0.05s system 13% cpu 3.641 total


# time python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map 'len(x) ! str(x) ! x[-1] ! int(x) ! x - 2 ! x * 5 ! str(x)' map '"http://httpbin.org/delay/" + x ! await asks.get(x) ! x.json() '  <<EOF
# http://httpbin.org/delay/3
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# EOF
