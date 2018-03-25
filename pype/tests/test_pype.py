
import pytest
from click.testing import CliRunner

import pype
import pype.app


@pytest.mark.parametrize(
    'args,  expected',
    [
        (['str.replace(?, ".", "!")', ('a.b.c',)], 'a!b!c\n'),
    ]
)
def test_cli(args, expected):

    runner = CliRunner()
    result = runner.invoke(pype.app.cli, args)
    assert not result.exception
    assert result.output == expected
