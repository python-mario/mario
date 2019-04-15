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
from typing import Dict
from typing import Any


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
from . import asynch
from . import interpret
from . import plug
from . import interfaces


async def call_traversal(
    self,
    traversal: interfaces.Traversal,
    items: AsyncIterable,
    exit_stack: async_exit_stack.AsyncExitStack,
):
    runtime_parameters = {"items": items, "exit_stack": exit_stack}

    calculated_params = traversal.plugin_object.calculate_more_params(traversal)

    available_params = collections.ChainMap(
        calculated_params,
        runtime_parameters,
        traversal.specific_invocation_params,
        traversal.global_invocation_options.global_options,
    )

    args = {
        param: available_params[param]
        for param in traversal.plugin_object.required_parameters
    }

    return await traversal.plugin_object.traversal_function(**args)


async def program_runner(
    traversals: List[interfaces.Traversal],
    items: AsyncIterable,
    context: interfaces.Context,
):

    async with async_exit_stack.AsyncExitStack() as stack:
        for traversal in traversals:
            items = await call_traversal(context, traversal, items, stack)

        return stack.pop_all(), items


async def async_main(basic_traversals, **kwargs):
    stream = trio._unix_pipes.PipeReceiveStream(os.dup(0))
    receiver = asynch.TerminatedFrameReceiver(stream, b"\n")
    items = (item.decode() async for item in receiver)

    global_context = interfaces.Context(plug.global_registry.global_options.copy())
    global_context.global_options.update(config.DEFAULTS)
    global_context.global_options.update(kwargs)

    global_context.global_options[
        "global_namespace"
    ] = interpret.build_global_namespace(
        global_context.global_options["base_exec_before"]
    )

    global_context.global_options["global_namespace"].update(
        interpret.build_global_namespace(global_context.global_options["exec_before"])
    )

    traversals = []
    for bt in basic_traversals:
        for d in bt:
            traversal = interfaces.Traversal(
                global_invocation_options=global_context,
                specific_invocation_params=d,
                plugin_object=plug.global_registry.traversals[d["name"]],
            )
            traversals.append(traversal)

    stack, items = await program_runner(traversals, items, global_context)

    async with stack:
        async for item in items:
            print(item)


def main(pairs, **kwargs):
    trio.run(functools.partial(async_main, pairs, **kwargs))
