import io

import pytest
from click.testing import CliRunner

import pype
import pype.app


@pytest.mark.parametrize(
    'args, stdin, expected',
    [
        (['str.replace(?, ".", "!")'], 'a.b.c\n', 'a!b!c!'),
    ]
)
def test_cli(args, stdin, expected):

    runner = CliRunner()
    result = runner.invoke(pype.app.cli, args, input=stdin)
    assert not result.exception
    assert result.output == expected
