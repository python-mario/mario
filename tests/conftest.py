import os

import click.testing
import pytest


@pytest.fixture(name="runner")
def _runner():
    return click.testing.CliRunner()


@pytest.fixture(name="tmp_env")
def _tmp_env(tmp_path):
    env = os.environ.copy()
    env["MARIO_CONFIG_DIR"] = tmp_path
    return env
