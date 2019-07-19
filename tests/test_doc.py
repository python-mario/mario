import textwrap

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
