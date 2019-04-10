import os
import textwrap

import toml

from pype import utils

from . import tools


def test_base_exec_before(tmp_path):
    config_body = """
    base_exec_before = 's = "value "'
    """
    config_file_path = tmp_path / "config.toml"

    config_file_path.write_text(config_body)

    args = ["--exec-before", "t = 'is '", "map", "s+t+x"]
    stdin = "ab\ncd\n".encode()
    env = dict(os.environ)
    env.update({f"{utils.NAME}_CONFIG_DIR".upper().encode(): str(tmp_path).encode()})
    output = tools.run(args, input=stdin, env=env).decode()
    assert output == """value is ab\nvalue is cd\n"""


def test_config_jsonl_alias(tmp_path):

    config_body = (tools.TESTS_DIR / "data/config/jsonl_alias.toml").read_text()
    config_file_path = tmp_path / "config.toml"

    config_file_path.write_text(config_body)

    args = ["jsonl"]
    stdin = textwrap.dedent(
        """\
    {"a": 1, "b": 2}
    {"a": 3, "b": 4}
    """
    ).encode()
    env = dict(os.environ)
    env.update({f"{utils.NAME}_CONFIG_DIR".upper().encode(): str(tmp_path).encode()})
    output = tools.run(args, input=stdin, env=env).decode()
    assert output == textwrap.dedent(
        """\
    X(a=1, b=2)
    X(a=3, b=4)
    """
    )
