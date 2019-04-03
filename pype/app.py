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

import attr
import parso
import click
import click_default_group
import toolz
import trio


BUFSIZE = 2 ** 14
counter = itertools.count()
_RECEIVE_SIZE = 4096  # pretty arbitrary


class TerminatedFrameReceiver:
    """Parse frames out of a Trio stream, where each frame is terminated by a
    fixed byte sequence.

    For example, you can parse newline-terminated lines by setting the
    terminator to b"\n".

    This uses some tricks to protect against denial of service attacks:

    - It puts a limit on the maximum frame size, to avoid memory overflow; you
    might want to adjust the limit for your situation.

    - It uses some algorithmic trickiness to avoid "slow loris" attacks. All
      algorithms are amortized O(n) in the length of the input.

    """

    def __init__(
        self,
        stream: trio.abc.ReceiveStream,
        terminator: bytes,
        max_frame_length: int = 16384,
    ) -> None:
        self.stream = stream
        self.terminator = terminator
        self.max_frame_length = max_frame_length
        self._buf = bytearray()
        self._next_find_idx = 0

    async def receive(self) -> bytearray:
        while True:
            terminator_idx = self._buf.find(self.terminator, self._next_find_idx)
            if terminator_idx < 0:
                # no terminator found
                if len(self._buf) > self.max_frame_length:
                    raise ValueError("frame too long")
                # next time, start the search where this one left off
                self._next_find_idx = max(0, len(self._buf) - len(self.terminator) + 1)
                # add some more data, then loop around
                more_data = await self.stream.receive_some(_RECEIVE_SIZE)
                if more_data == b"":
                    if self._buf:
                        raise ValueError("incomplete frame")
                    raise trio.EndOfChannel
                self._buf += more_data
            else:
                # terminator found in buf, so extract the frame
                frame = self._buf[:terminator_idx]
                # Update the buffer in place, to take advantage of bytearray's
                # optimized delete-from-beginning feature.
                del self._buf[: terminator_idx + len(self.terminator)]
                # next time, start the search from the beginning
                self._next_find_idx = 0
                return frame

    def __aiter__(self) -> "TerminatedFrameReceiver":
        return self

    async def __anext__(self) -> bytearray:
        try:
            return await self.receive()
        except trio.EndOfChannel:
            raise StopAsyncIteration


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


def split_pipestring(command):
    # TODO Use a real parser.
    return [s.strip() for s in command.split("!")]


def build_source(components):
    components = [c.strip() for c in components]
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


def build_function(command):
    name_to_module = build_name_to_module(command)

    source = build_source(split_pipestring(command))

    local_namespace = {}
    global_namespace = name_to_module.copy()

    exec(source, global_namespace, local_namespace)
    function = local_namespace["_pype_runner"]
    return function


async def handle_item(function, item):
    return await function(item)


async def item_handler(function, item):
    yield (await handle_item(function, item.decode()))


async def async_map(function, iterable):
    results = []

    async def _item_handler(function, item):
        results.append(await function(item))

    async with trio.open_nursery() as nursery:
        async for item in iterable:
            nursery.start_soon(_item_handler, function, item)

    return results


async def async_filter(function, iterable):
    return filter(function, await (await item async for item in iterable))


async def async_apply(function, iterable):
    return function((await item) for item in iterable)


async def program_runner(pairs, items):
    for how, what in pairs:
        what = build_function(what)

        if how == "map":
            items = await async_map(what, items)

        elif how == "apply":
            applied = await async_apply(what, items)

        elif how == "filter":
            items = await async_filter(what, items)
        else:
            raise ValueError(how)


async def async_main(pairs,):
    stream = trio._unix_pipes.PipeReceiveStream(os.dup(0))
    receiver = TerminatedFrameReceiver(stream, b"\n")
    decoded = (item.decode() async for item in receiver)
    await program_runner(pairs, decoded)


def main(pairs):
    trio.run(async_main, pairs)


@click.group(chain=True)
def cli(**kwargs):
    pass


@cli.command("map")
@click.argument("command")
def cli_map(command):
    return ("map", command)


@cli.command("apply")
@click.argument("command")
def cli_apply(command):
    return ("apply", command)


@cli.command("filter")
@click.argument("command")
def cli_filter(command):
    return ("filter", command)


@cli.resultcallback()
def collect(pairs):
    main(pairs)
