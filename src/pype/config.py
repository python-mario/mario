import pathlib

import appdirs
import toml

from . import utils
from . import interpret

DEFAULTS = {
    "max_concurrent": 5,
    "exec_before": None,
    "autocall": interpret.HowCall.SINGLE,
    "base_exec_before": None,
}


def get_config_dir():
    return pathlib.Path(appdirs.user_config_dir(utils.NAME))


def load_config(dir_path=None):
    if dir_path is None:
        config_dir = get_config_dir()
    else:
        config_dir = pathlib.Path(dir_path)

    config_path = config_dir / "config.toml"

    try:
        with open(config_path) as f:
            return toml.load(f)
    except OSError:
        return {}
