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

T = typing.TypeVar("T")
U = typing.TypeVar("U")

_PYPE_VALUE = "_PYPE_VALUE"

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


class AsyncIterableWrapper:
    def __init__(self, iterable):
        self.iterable = iter(iterable)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iterable)
        except StopIteration:
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


@async_generator.asynccontextmanager
async def async_map(
    function: Callable[[T], Awaitable[U]], iterable: AsyncIterable[T], concurrent_max
) -> AsyncIterator[AsyncIterable[U]]:
    send_result, receive_result = trio.open_memory_channel[U](0)
    limiter = trio.CapacityLimiter(concurrent_max)

    async def wrapper(prev_done: trio.Event, self_done: trio.Event, item: T) -> None:
        maybe_coroutine_result = function(item)
        if isinstance(maybe_coroutine_result, types.CoroutineType):
            async with limiter:
                result = await maybe_coroutine_result
        else:
            result = maybe_coroutine_result
        await prev_done.wait()
        await send_result.send(result)
        self_done.set()

    async def consume_input(nursery) -> None:
        prev_done = trio.Event()
        prev_done.set()
        async for item in iterable:
            self_done = trio.Event()
            nursery.start_soon(wrapper, prev_done, self_done, item, name=function)
            prev_done = self_done
        await prev_done.wait()
        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


@async_generator.asynccontextmanager
async def async_filter(
    function: Callable[[T], Awaitable[T]], iterable: AsyncIterable[T], concurrent_max
) -> AsyncIterator[AsyncIterable[T]]:
    send_result, receive_result = trio.open_memory_channel[T](0)

    limiter = trio.CapacityLimiter(concurrent_max)

    async def wrapper(prev_done: trio.Event, self_done: trio.Event, item: T) -> None:

        maybe_coroutine_result = function(item)
        if isinstance(maybe_coroutine_result, types.CoroutineType):
            async with limiter:
                result = await maybe_coroutine_result
        else:
            result = maybe_coroutine_result

        await prev_done.wait()
        if result:
            await send_result.send(item)
        self_done.set()

    async def consume_input(nursery) -> None:
        prev_done = trio.Event()
        prev_done.set()
        async for item in iterable:
            self_done = trio.Event()
            nursery.start_soon(wrapper, prev_done, self_done, item, name=function)
            prev_done = self_done
        await prev_done.wait()
        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


async def program_runner(pairs, items, concurrent_max):

    async with async_exit_stack.AsyncExitStack() as stack:

        for how, function in pairs:

            if how == "map":
                items = await stack.enter_async_context(
                    async_map(function, items, concurrent_max)
                )

            elif how == "filter":
                items = await stack.enter_async_context(
                    async_filter(function, items, concurrent_max)
                )

            elif how == "apply":
                items = AsyncIterableWrapper([await function([x async for x in items])])

            elif how == "eval":
                items = AsyncIterableWrapper([await function(None)])

        async for item in items:
            print(item)


async def async_main(pairs, max_concurrent):
    stream = trio._unix_pipes.PipeReceiveStream(os.dup(0))
    receiver = TerminatedFrameReceiver(stream, b"\n")
    result = (item.decode() async for item in receiver)

    pairs = [(how, build_function(what)) for how, what in pairs]

    result = await program_runner(pairs, result, max_concurrent)


def main(pairs, **kwargs):
    trio.run(functools.partial(async_main, pairs, **kwargs))


@click.group(chain=True)
@click.option("--max-concurrent", type=int, default=5)
@click.version_option(_version.__version__, prog_name="pype")
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


@cli.command("eval")
@click.argument("command")
def cli_eval(command):
    return ("eval", command)


@cli.resultcallback()
def collect(pairs, **kwargs):
    main(pairs, **kwargs)


# time python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map 'len(x)' filter 'x < 195' apply 'len(x)' <<EOF
# http://httpbin.org/delay/3
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# EOF
# 8
# python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map   0.45s user 0.05s system 13% cpu 3.641 total


# time python3.7 -m poetry run python -m pype map 'await asks.get(x) ! x.body ' map 'len(x) ! str(x) ! x[-1] ! int(x) ! x - 2 ! x * 5 ! str(x)' map '"http://httpbin.org/delay/" + x ! await asks.get(x) ! x.json() '  <<EOF
# http://httpbin.org/delay/3
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# http://httpbin.org/delay/1
# EOF
