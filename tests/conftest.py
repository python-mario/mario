import click.testing
import pytest


@pytest.fixture(name="runner")
def _runner():
    return click.testing.CliRunner()
