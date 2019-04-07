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


try:
    import asks
except ImportError:
    pass
else:
    asks.init("trio")


from . import _version
from . import config
from . import utils
from . import asynch
from . import interpret


async def program_runner(pairs, items, max_concurrent):

    async with async_exit_stack.AsyncExitStack() as stack:

        for how, function in pairs:

            if how == "map":
                items = await stack.enter_async_context(
                    asynch.async_map(function, items, max_concurrent)
                )

            elif how == "filter":
                items = await stack.enter_async_context(
                    asynch.async_filter(function, items, max_concurrent)
                )

            elif how == "apply":
                items = asynch.AsyncIterableWrapper(
                    [await function([x async for x in items])]
                )

            elif how == "eval":
                items = asynch.AsyncIterableWrapper([await function(None)])

            elif how == "stack":
                items = asynch.AsyncIterableWrapper(
                    [await function("".join([x + "\n" async for x in items]))]
                )

            else:
                raise NotImplementedError(how)

        return stack.pop_all(), items


async def async_main(
    pairs,
    max_concurrent=config.DEFAULTS["max_concurrent"],
    exec_before=config.DEFAULTS["exec_before"],
    autocall=config.DEFAULTS["autocall"],
):
    stream = trio._unix_pipes.PipeReceiveStream(os.dup(0))
    receiver = asynch.TerminatedFrameReceiver(stream, b"\n")
    result = (item.decode() async for item in receiver)

    global_namespace = interpret.build_global_namespace(exec_before)
    pairs = [
        (how, interpret.build_function(what, global_namespace, autocall))
        for how, what in pairs
    ]

    stack, items = await program_runner(pairs, result, max_concurrent)

    async with stack:
        async for item in items:
            print(item)


def main(pairs, **kwargs):
    trio.run(functools.partial(async_main, pairs, **kwargs))
