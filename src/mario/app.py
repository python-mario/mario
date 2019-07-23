#!/usr/bin/env python
"""Command line pipes in python."""

from __future__ import generator_stop

import collections
import functools
import os
from typing import AsyncIterable
from typing import List

import async_exit_stack
import attr
import trio

from . import asynch
from . import config
from . import interfaces
from . import interpret
from . import plug


async def call_traversal(
    context,  # pylint: disable=unused-argument
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
    # pylint: disable=protected-access
    stream = trio._unix_pipes.PipeReceiveStream(os.dup(0))
    receiver = asynch.TerminatedFrameReceiver(stream, b"\n")
    items = (item.decode() async for item in receiver)

    # pylint: disable=no-member
    global_context = interfaces.Context(global_registry.global_options.copy())
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
            # pylint: disable=fixme
            # TODO Make classes or use pyrsistent.
            traversal_namespace = {
                **global_context.global_options["global_namespace"],
                **d["parameters"].get("inject_values", {"HELLO": "WORLD"}),
            }
            traversal_context = attr.evolve(
                global_context,
                global_options=dict(
                    global_context.global_options, global_namespace=traversal_namespace
                ),
            )
            # pylint: disable=unsubscriptable-object
            traversal = interfaces.Traversal(
                global_invocation_options=traversal_context,
                specific_invocation_params=d,
                plugin_object=global_registry.traversals[d["name"]],
            )
            traversals.append(traversal)

    stack, items = await program_runner(traversals, items, global_context)

    async with stack:
        async for item in items:
            print(item)


def main(pairs, **kwargs):
    trio.run(functools.partial(async_main, pairs, **kwargs))


global_registry = plug.make_global_registry()
