#!/usr/bin/env python
"""Command line pipes in python."""

from __future__ import generator_stop


import collections
import importlib
import io
import os
import sys
import textwrap
import token
import tokenize
import itertools
import re
import contextlib
import typing
import types
import functools
import pathlib

from typing import Callable
from typing import Awaitable
from typing import AsyncIterable
from typing import AsyncIterator
from typing import Optional
from typing import List

import attr
import parso
import click
import click_default_group
import toolz
import trio
import async_generator
import async_exit_stack


from . import _version
from . import config
from . import utils


def _get_named_module(name):
    builtins = sys.modules["builtins"]
    if hasattr(builtins, name):
        return builtins
    try:
        return __import__(name, {}, {})
    except ImportError as e:
        pass
    raise LookupError(f"Could not find {name}")


def _get_autoimport_module(fullname):
    name_parts = fullname.split(".")
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, ".".join(name_parts[: idx + 1]))

    for name in try_names:
        try:
            module = _get_named_module(name)
        except LookupError:
            pass
        else:
            if module is sys.modules["builtins"]:
                return {}
            return {name: module}

    return {}


def find_maybe_module_names(text):
    # TODO: Use a real parser.
    return re.findall(r"\b[^\d\W]\w*(?:\.[^\d\W]\w*)+\b", text)


def split_pipestring(s, sep="!"):
    segments = []
    tree = parso.parse(s)
    current_nodes = []

    for c in tree.children:
        if isinstance(c, parso.python.tree.PythonErrorLeaf) and c.value == sep:
            segments.append(current_nodes)
            current_nodes = []
        else:
            current_nodes.append(c)

    segments.append(current_nodes)

    return ["".join(node.get_code() for node in seg) for seg in segments]


def test_split_pipestring():
    s = 'x ! y + f"{x!r}"'
    sep = "!"
    assert split_pipestring(s, sep) == ["x", ' y + f"{x!r}"']


def make_autocall(expression):
    if expression.endswith(")"):
        return expression
    return expression + "(x)"


def build_source(components, autocall):
    components = [c.strip() for c in components]
    if autocall:
        components = [make_autocall(c) for c in components]
    indent = "        "
    lines = "".join([f"{indent}x = {c}\n" for c in components])

    source = textwrap.dedent(
        f"""\
    async def _pype_runner(x):
{lines}
        return x
    """
    )
    return source


def build_name_to_module(command):
    name_to_module = {}
    components = split_pipestring(command)
    module_names = {name for c in components for name in find_maybe_module_names(c)}
    for name in module_names:
        name_to_module.update(_get_autoimport_module(name))

    return name_to_module


def build_function(command, global_namespace, autocall):
    name_to_module = build_name_to_module(command)
    global_namespace = {**name_to_module, **global_namespace}

    source = build_source(split_pipestring(command), autocall)

    local_namespace = {}

    exec(source, global_namespace, local_namespace)
    function = local_namespace["_pype_runner"]
    return function


def build_global_namespace(source):
    if source is None:
        return {}
    namespace = {}
    exec(source, {}, namespace)
    return namespace
