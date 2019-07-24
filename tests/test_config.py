import os
import textwrap

from mario import utils

from . import helpers


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
    output = helpers.run(args, input=stdin, env=env).decode()
    assert output == """value is ab\nvalue is cd\n"""


def test_config_jsonl_command(tmp_path):

    config_body = (helpers.TESTS_DIR / "data/config/jsonl_command.toml").read_text()
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
    output = helpers.run(args, input=stdin, env=env).decode()
    assert output == textwrap.dedent(
        """\
    {'a': 1, 'b': 2}
    {'a': 3, 'b': 4}
    """
    )


def test_m_namespace(tmp_path, tmp_env):
    """The init file is available under the ``m`` namespace."""
    file = tmp_path / "m" / "__init__.py"
    file.parent.mkdir()
    file.write_text("var = 1\n")
    result = helpers.run(["eval", "m.var"], env=tmp_env).decode()
    assert result == "1\n"


def test_m_init_executed_at_startup(tmp_path, tmp_env):
    """The init file is executed at startup time."""
    file = tmp_path / "m" / "__init__.py"
    file.parent.mkdir()
    file.write_text("print('hello')")
    result = helpers.run(["eval", '""'], env=tmp_env).decode()
    assert result == "hello\n\n"


def test_m_submodule(tmp_path, tmp_env):
    """The submodule is available under the ``m`` namespace."""
    file = tmp_path / "m" / "example.py"
    file.parent.mkdir()
    file.write_text("var = 1\n")
    result = helpers.run(["eval", "m.example.var"], env=tmp_env).decode()
    assert result == "1\n"


def test_m_submodule_not_executed_at_startup(tmp_path, tmp_env):
    """The submodule is *not* executed at startup."""
    file = tmp_path / "m" / "example.py"
    file.parent.mkdir()
    file.write_text("print('hello')")
    result = helpers.run(["eval", "''"], env=tmp_env).decode()
    assert result == "\n"


def test_hidden_false(tmp_path, tmp_env):
    """Non-hidden commands do appear in --help."""

    text = """
    [[command]]
    name = "my-visible-command"
    hidden = false

    [[command.stages]]
    command = "eval"
    params = {code='1'}
    """

    (tmp_path / "config.toml").write_text(text)

    result = helpers.run(["--help"], env=tmp_env).decode()
    assert "my-visible-command" in result


def test_hidden_true(tmp_path, tmp_env):
    """Hidden commands don't appear in --help."""

    text = """
    [[command]]
    name = "my-hidden-command"
    hidden = true

    [[command.stages]]
    command = "eval"
    params = {code='1'}
    """

    (tmp_path / "config.toml").write_text(text)

    result = helpers.run(["--help"], env=tmp_env).decode()
    assert "my-hidden-command" not in result
