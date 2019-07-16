import click

from mario import asynch
from mario import interpret
from mario import plug
from mario import traversals


registry = plug.Registry()


def calculate_function(traversal, howcall=None):
    if howcall is None:
        howcall = traversal.specific_invocation_params.get("howcall")
    if howcall is None:
        howcall = interpret.HowCall.SINGLE

    global_namespace = traversal.global_invocation_options.global_options[
        "global_namespace"
    ].copy()

    if "exec_before" in traversal.specific_invocation_params["parameters"]:
        global_namespace.update(
            interpret.build_global_namespace(
                traversal.specific_invocation_params["parameters"]["exec_before"]
            )
        )

    if "code" in traversal.specific_invocation_params:

        return {
            "function": interpret.build_function(
                traversal.specific_invocation_params["code"],
                global_namespace=global_namespace,
                howcall=howcall,
            )
        }

    return {"function": None}


def calculate_reduce(traversal):

    function = interpret.build_function(
        traversal.specific_invocation_params["code"],
        traversal.global_invocation_options.global_options["global_namespace"],
        howcall=interpret.HowCall.VARARGS,
    )

    return {"function": function}


@registry.add_traversal("map", calculate_more_params=calculate_function)
async def map(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.sync_map(function, items, max_concurrent)
    )


@registry.add_traversal("async_map", calculate_more_params=calculate_function)
async def async_map(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_map(function, items, max_concurrent)
    )


@registry.add_traversal("async_map_unordered", calculate_more_params=calculate_function)
async def map_unordered(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_map_unordered(function, items, max_concurrent)
    )


@registry.add_traversal("filter", calculate_more_params=calculate_function)
async def filter(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.sync_filter(function, items, max_concurrent)
    )


@registry.add_traversal("async_filter", calculate_more_params=calculate_function)
async def async_filter(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_filter(function, items, max_concurrent)
    )


@registry.add_traversal("apply", calculate_more_params=calculate_function)
async def apply(function, items):
    """When ``function`` takes an iterable."""
    return traversals.AsyncIterableWrapper([await function([x async for x in items])])


@registry.add_traversal("async_apply", calculate_more_params=calculate_function)
async def async_apply(function, items):
    """When ``function`` takes an async iterable."""
    return await traversals.async_apply(function, items)


@registry.add_traversal(
    "eval",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def eval(function):
    return traversals.AsyncIterableWrapper([await function(None)])


@registry.add_traversal("stack", calculate_more_params=calculate_function)
async def stack(function, items):
    return traversals.AsyncIterableWrapper(
        [await function("".join([x + "\n" async for x in items]))]
    )


@registry.add_traversal("reduce", calculate_more_params=calculate_reduce)
async def reduce(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_reduce(function, items, max_concurrent)
    )


@registry.add_traversal("dropwhile", calculate_more_params=calculate_function)
async def dropwhile(function, items, exit_stack):
    return await exit_stack.enter_async_context(
        traversals.sync_dropwhile(function, items)
    )


@registry.add_traversal(
    "chain",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def chain(items, exit_stack):
    return await exit_stack.enter_async_context(traversals.sync_chain(items))


@registry.add_traversal(
    "async-chain",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def async_chain(items, exit_stack):
    return await exit_stack.enter_async_context(traversals.async_chain(items))


subcommands = [
    click.Command("map", short_help="Call <code> on each line of input."),
    click.Command("async-map", short_help="Call <code> on each line of input."),
    click.Command("apply", short_help="Call <code> on input as a sequence."),
    click.Command(
        "async-apply", short_help="Call <code> asynchronously on input as a sequence."
    ),
    click.Command(
        "filter",
        short_help="Call <code> on each line of input and exclude false values.",
    ),
    click.Command(
        "async-filter",
        short_help="Async call <code> on each line of input and exclude false values.",
    ),
    click.Command(
        "stack", short_help="Call <code> on input as a single concatenated string."
    ),
    click.Command(
        "async-map-unordered",
        short_help="Call <code> on each line of input, ignoring order of input items.",
    ),
    click.Command(
        "dropwhile",
        short_help="Evaluate <predicate> on function and drop values until first falsy.",
    ),
    click.Command("eval", short_help="Evaluate a python expression <code>"),
]


def build_callback(sub_command):
    def callback(code, autocall, **parameters):
        if autocall:
            howcall = interpret.HowCall.SINGLE
        else:
            howcall = interpret.HowCall.NONE

        return [
            {
                "name": sub_command.name.replace("-", "_"),
                "howcall": howcall,
                "code": code,
                "parameters": parameters,
            }
        ]

    return callback


option_exec_before = click.option(
    "--exec-before", help="Execute code in the function's global namespace."
)

for subcommand in subcommands:

    subcommand.params = [
        click.Option(["--autocall/--no-autocall"], is_flag=True, default=True),
        click.Argument(["code"]),
    ]
    subcommand.callback = build_callback(subcommand)
    subcommand = option_exec_before(subcommand)
    # TODO: add_cli and add_traversal should be the non-decorator form
    registry.add_cli(name=subcommand.name)(subcommand)


@registry.add_cli(name="reduce")
@click.command(
    "reduce", short_help="Reduce a sequence with a <function>. e.g. `operator.mul`."
)
@option_exec_before
@click.argument("function_name")
def _reduce(function_name, **parameters):
    return [
        {
            "code": f"toolz.curry({function_name})",
            "name": "reduce",
            "parameters": parameters,
        }
    ]


# @registry.add_cli(name="eval")
# @click.command("eval", short_help="Call <code> without any input.")
# @option_exec_before
# @click.argument("expression")
# def _eval(expression, **parameters):
#     return [{"code": expression, "name": "eval", "parameters": parameters}]


more_commands = [
    click.Command(
        "chain",
        callback=lambda **kw: [{"name": "chain", "parameters": kw}],
        short_help="Expand iterable of iterables of items into an iterable of items.",
    ),
    click.Command(
        "async-chain",
        callback=lambda **kw: [{"name": "async-chain", "parameters": kw}],
        short_help="Expand iterable of async iterables into an iterable of items.",
    ),
]
for cmd in more_commands:
    registry.add_cli(name=cmd.name)(cmd)
