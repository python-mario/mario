from __future__ import annotations
from __future__ import generator_stop

import functools
import itertools
import threading
import types
import typing as t
from typing import AsyncIterable
from typing import AsyncIterator
from typing import Awaitable
from typing import Callable
from typing import Iterable

import async_generator
import trio
import trio_typing


T = t.TypeVar("T")
U = t.TypeVar("U")

_PYPE_VALUE = "_PYPE_VALUE"

BUFSIZE = 2 ** 14
counter = itertools.count()
_RECEIVE_SIZE = 4096  # pretty arbitrary


async def aenumerate(items, start=0):
    i = start
    async for x in items:
        yield i, x
        i += 1


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


class AsyncIterableToIterable:
    def __init__(self, aiterable):
        self.aiterable = aiterable

    def __iter__(self):
        return self

    async def __next__(self):
        return await self.aiterable.__anext__()


class IterableToAsyncIterable:
    def __init__(self, iterable):
        self.iterable = iter(iterable)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iterable)
        except StopIteration:
            raise StopAsyncIteration


T = t.TypeVar("T")


def _pull_values_from_async_iterator(
    in_trio: trio.BlockingTrioPortal,
    ait: t.AsyncIterator[T],
    send_to_trio: trio.abc.SendChannel[T],
):
    """Make a generator by asking Trio to async-iterate over the async iterable,
    then yield the results.

    This function is run in a thread.
    """
    while True:
        try:
            yield in_trio.run(ait.__anext__)
        except StopAsyncIteration:
            break


def _threaded_sync_apply(
    in_trio: trio.BlockingTrioPortal,
    function: t.Callable[[t.Iterable[T]], t.Any],
    send_to_trio: trio.abc.SendChannel,
    ait: t.AsyncIterator[T],
    receive_from_thread: trio.abc.ReceiveChannel,
    iterator=None,
):
    """Extract values from async iterable into a sync iterator, apply function to
    it, and send the result back into Trio.

    This function is run in a thread.

    """

    try:
        for x in iterator:
            in_trio.run(send_to_trio.send, x)
    finally:
        in_trio.run(send_to_trio.aclose)


async def sync_apply(
    sync_function: t.Callable[[t.Iterable[T]], t.Any], data: t.AsyncIterable[T]
):
    """Apply a sync Callable[Iterable] to an async iterable by pulling values in a
    thread.
    """
    in_trio = trio.BlockingTrioPortal()
    send_to_trio, receive_from_thread = trio.open_memory_channel[t.Tuple[T, t.Any]](0)

    async with trio.open_nursery() as n:

        iterator = await sync_function(
            _pull_values_from_async_iterator(in_trio, data, send_to_trio)
        )
        n.start_soon(
            trio.run_sync_in_worker_thread,
            functools.partial(
                _threaded_sync_apply,
                function=sync_function,
                iterator=iterator,
                ait=data,
                in_trio=in_trio,
                send_to_trio=send_to_trio,
                receive_from_thread=receive_from_thread,
            ),
        )

        async for x in receive_from_thread:
            yield x


def wrap_sync_fold(function):
    @functools.wraps(function)
    def wrap(items):
        yield from [function(items)]

    return wrap


async def async_apply(function, data):
    return await function(data)


@async_generator.asynccontextmanager
async def async_map(
    function: Callable[[T], Awaitable[U]], iterable: AsyncIterable[T], max_concurrent
) -> AsyncIterator[AsyncIterable[U]]:
    send_result, receive_result = trio.open_memory_channel[U](0)
    limiter = trio.CapacityLimiter(max_concurrent)

    async def wrapper(prev_done: trio.Event, self_done: trio.Event, item: T) -> None:

        async with limiter:
            result = await function(item)

        await prev_done.wait()
        await send_result.send(result)
        self_done.set()

    async def consume_input(nursery) -> None:
        prev_done = trio.Event()
        prev_done.set()
        async for item in iterable:
            self_done = trio.Event()
            nursery.start_soon(wrapper, prev_done, self_done, item)
            prev_done = self_done
        await prev_done.wait()
        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


@async_generator.asynccontextmanager
async def sync_map(
    function: Callable[[T], Awaitable[U]], iterable: AsyncIterable[T], max_concurrent
) -> AsyncIterator[AsyncIterable[U]]:
    yield (await function(item) async for item in iterable)


@async_generator.asynccontextmanager
async def sync_chain(iterable: AsyncIterable[Iterable], **kwargs):
    yield (item async for subiterable in iterable for item in subiterable)


@async_generator.asynccontextmanager
async def async_chain(iterable: AsyncIterable[AsyncIterable], **kwargs):
    yield (item async for subiterable in iterable async for item in subiterable)


@async_generator.asynccontextmanager
async def sync_filter(
    function: Callable[[T], Awaitable[U]], iterable: AsyncIterable[T], max_concurrent
) -> AsyncIterator[AsyncIterable[U]]:
    yield (item async for item in iterable if await function(item))


@async_generator.asynccontextmanager
async def async_map_unordered(
    function: Callable[[T], Awaitable[U]], iterable: AsyncIterable[T], max_concurrent
) -> AsyncIterator[AsyncIterable[U]]:
    send_result, receive_result = trio.open_memory_channel[U](0)
    limiter = trio.CapacityLimiter(max_concurrent)
    remaining_tasks: Set[int] = set()

    async def wrapper(task_id: int, item: T) -> None:
        async with limiter:
            result = await function(item)

        await send_result.send(result)
        remaining_tasks.remove(task_id)

    async def consume_input(nursery) -> None:

        async for task_id, item in aenumerate(iterable):
            remaining_tasks.add(task_id)
            nursery.start_soon(wrapper, task_id, item)

        while remaining_tasks:
            await trio.sleep(0)

        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


@async_generator.asynccontextmanager
async def async_filter(
    function: Callable[[T], Awaitable[T]], iterable: AsyncIterable[T], max_concurrent
) -> AsyncIterator[AsyncIterable[T]]:
    send_result, receive_result = trio.open_memory_channel[T](0)

    limiter = trio.CapacityLimiter(max_concurrent)

    async def wrapper(prev_done: trio.Event, self_done: trio.Event, item: T) -> None:

        async with limiter:
            result = await function(item)

        await prev_done.wait()
        if result:
            await send_result.send(item)
        self_done.set()

    async def consume_input(nursery) -> None:
        prev_done = trio.Event()
        prev_done.set()
        async for item in iterable:
            self_done = trio.Event()
            nursery.start_soon(wrapper, prev_done, self_done, item)
            prev_done = self_done
        await prev_done.wait()
        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


SENTINEL = object()


@async_generator.asynccontextmanager
async def async_reduce(
    function: Callable[[T], Awaitable[U]],
    iterable: AsyncIterable[T],
    max_concurrent,
    initializer=SENTINEL,
) -> AsyncIterator[AsyncIterable[U]]:
    send_result, receive_result = trio.open_memory_channel[U](0)
    limiter = trio.CapacityLimiter(max_concurrent)

    collected_result = initializer

    async def wrapper(prev_done: trio.Event, self_done: trio.Event, item: T) -> None:
        nonlocal collected_result

        input_item = await wait_for(item)

        if collected_result is SENTINEL:
            # We are working on the first item, and initializer was not set.
            collected_result = input_item

        else:

            async with limiter:
                collected_result = await function(collected_result, input_item)

        await prev_done.wait()
        self_done.set()

    async def consume_input(nursery) -> None:
        prev_done = trio.Event()
        prev_done.set()
        async for item in iterable:
            self_done = trio.Event()
            nursery.start_soon(wrapper, prev_done, self_done, item)
            prev_done = self_done
        await prev_done.wait()
        await send_result.send(collected_result)
        await send_result.aclose()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(consume_input, nursery)
        yield receive_result
        nursery.cancel_scope.cancel()


async def wait_for(x):
    if isinstance(x, types.CoroutineType):
        return await x
    return x


@async_generator.asynccontextmanager
async def sync_dropwhile(predicate, aiterable):
    async def wrap(ait):

        async for x in ait:
            if await predicate(x):
                continue
            else:
                yield x
                break

        async for x in ait:
            yield x

    yield wrap(aiterable)
