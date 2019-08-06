import textwrap

from tests import helpers

import mario.doc


def test_rst2text():
    source = textwrap.dedent(
        """\
    ============
    Introduction
    ============

    Hello world.

    .. code-block:: bash

        $ echo Greetings.


    """
    )

    result = mario.doc.rst2text(source)
    expected = textwrap.dedent(
        """\
    Introduction
    ============

    Hello world.

       $ echo Greetings.
    """
    )
    assert result == expected


def test_help():
    """CLI help is formatted as plain text not rst and includes a demo."""
    result = helpers.run(["map", "--help"]).decode()

    assert "$ mario map" in result
    assert ".. code-block" not in result


def test_render_short_help(tmp_path, tmp_env):
    """CLI renders ``short_help`` if ``help`` is missing."""
    result = helpers.run(["map", "--help"]).decode()
    text = """
    [[command]]
    name = "my-command"
    short_help = "This is the short help."

    [[command.stages]]
    command = "eval"
    params = {code='1'}
    """

    (tmp_path / "config.toml").write_text(text)

    result = helpers.run(["my-command", "--help"], env=tmp_env).decode()

    assert "This is the short help." in result
