import pathlib

import appdirs
import toml

from . import utils

DEFAULTS = {"max_concurrent": 5, "exec_before": None, "autocall": True}


def load_config(dir_path=None):
    if dir_path is None:
        config_dir = pathlib.Path(appdirs.user_config_dir(utils.NAME))
    else:
        config_dir = pathlib.Path(dir_path)

    config_path = config_dir / "config.toml"

    try:
        with open(config_path) as f:
            return toml.load(f)
    except OSError:
        return {}
