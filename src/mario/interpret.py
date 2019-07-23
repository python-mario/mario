#!/usr/bin/env python
"""Command line pipes in python."""

from __future__ import annotations
from __future__ import generator_stop

import ast
import enum
import importlib
import re
import sys
import textwrap
import types

import attr
import parso


SYMBOL = "x"


class HowCall(enum.Enum):
    NONE = ""
    SINGLE = f"({SYMBOL})"
    VARARGS = f"(*{SYMBOL})"
    VARKWARGS = f"(**{SYMBOL})"


class HowSig(enum.Enum):
    NONE = f"{SYMBOL}"
    SINGLE = f"{SYMBOL}"
    VARARGS = f"*{SYMBOL}"
    VARKWARGS = f"**{SYMBOL}"


howcall_to_howsig = {v: HowSig.__members__[k] for k, v in HowCall.__members__.items()}


@attr.dataclass
class Function:
    wrapped: types.FunctionType
    global_namespace: dict
    source: str

    def __call__(self, *x):
        return self.wrapped(*x)


def _get_named_module(name):
    builtins = sys.modules["builtins"]
    if hasattr(builtins, name):
        return builtins
    try:
        return importlib.import_module(name)
    except ImportError:
        pass
    raise LookupError(f"Could not find {name}")


def _get_autoimport_module(fullname):
    name_parts = fullname.split(".")
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, ".".join(name_parts[: idx + 1]))

    name_to_module = {}
    for name in try_names:
        try:
            module = _get_named_module(name)
        except LookupError:
            pass
        else:
            if module is sys.modules["builtins"]:
                return {}
            name_to_module[name] = module

    return name_to_module


def find_maybe_module_names(text):
    # pylint: disable=fixme
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


def make_autocall(expression, howcall):

    # Don't autocall if SYMBOL appears in the expression.
    tree = ast.parse(expression)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == SYMBOL:
            return expression

    return expression + howcall.value


def build_source(components, howcall):
    components = [c.strip() for c in components]
    components = [make_autocall(c, howcall) for c in components]
    indent = "        "
    lines = "".join([f"{indent}{SYMBOL} = {c}\n" for c in components])

    howsig = howcall_to_howsig[howcall]
    source = textwrap.dedent(
        f"""\
    async def _mario_runner({howsig.value}):
{lines}
        return {SYMBOL}
    """
    )

    return source


def build_name_to_module(code):
    name_to_module = {}
    components = split_pipestring(code)
    module_names = {name for c in components for name in find_maybe_module_names(c)}
    for name in module_names:
        name_to_module.update(_get_autoimport_module(name))

    return name_to_module


def build_function(code, global_namespace, howcall):
    name_to_module = build_name_to_module(code)
    global_namespace = {**name_to_module, **global_namespace}

    source = build_source(split_pipestring(code), howcall)
    # pylint: disable=exec-used
    exec(source, global_namespace)
    function = global_namespace["_mario_runner"]
    return Function(function, global_namespace, source)


def build_global_namespace(source):
    if source is None:
        return {}
    global_namespace = {}

    # pylint: disable=exec-used
    exec(source, global_namespace)

    return global_namespace
