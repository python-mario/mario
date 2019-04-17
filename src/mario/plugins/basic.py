import click

from mario import plug
from mario import asynch
from mario import interpret
from mario import traversals

registry = plug.Registry()


def calculate_function(traversal, howcall=None):
    if howcall is None:
        howcall = traversal.specific_invocation_params.get("howcall")
    if howcall is None:
        howcall = interpret.HowCall.SINGLE
    return {
        "function": interpret.build_function(
            traversal.specific_invocation_params["pipeline"],
            global_namespace=traversal.global_invocation_options.global_options[
                "global_namespace"
            ],
            howcall=howcall,
        )
    }


def calculate_reduce(traversal):

    function = interpret.build_function(
        traversal.specific_invocation_params["pipeline"],
        traversal.global_invocation_options.global_options["global_namespace"],
        howcall=interpret.HowCall.VARARGS,
    )

    return {"function": function}


@registry.add_traversal("map", calculate_more_params=calculate_function)
async def map(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.sync_map(function, items, max_concurrent)
    )


@registry.add_traversal("amap", calculate_more_params=calculate_function)
async def amap(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_map(function, items, max_concurrent)
    )


@registry.add_traversal("amap_unordered", calculate_more_params=calculate_function)
async def map_unordered(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_map_unordered(function, items, max_concurrent)
    )


@registry.add_traversal("filter", calculate_more_params=calculate_function)
async def filter(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.sync_filter(function, items, max_concurrent)
    )


@registry.add_traversal("afilter", calculate_more_params=calculate_function)
async def afilter(function, items, exit_stack, max_concurrent):
    return await exit_stack.enter_async_context(
        traversals.async_filter(function, items, max_concurrent)
    )


@registry.add_traversal("apply", calculate_more_params=calculate_function)
async def apply(function, items):
    return traversals.AsyncIterableWrapper([await function([x async for x in items])])


@registry.add_traversal("aapply", calculate_more_params=calculate_function)
async def aapply(function, items):
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


subcommands = [
    click.Command("map", short_help="Call <pipeline> on each line of input."),
    click.Command("amap", short_help="Call <pipeline> on each line of input."),
    click.Command("apply", short_help="Call <pipeline> on input as a sequence."),
    click.Command(
        "aapply", short_help="Call <pipeline> asynchronously on input as a sequence."
    ),
    click.Command(
        "filter",
        short_help="Call <pipeline> on each line of input and exclude false values.",
    ),
    click.Command(
        "afilter",
        short_help="Async call <pipeline> on each line of input and exclude false values.",
    ),
    click.Command(
        "stack", short_help="Call <pipeline> on input as a single concatenated string."
    ),
    click.Command(
        "amap-unordered",
        short_help="Call <pipeline> on each line of input, ignoring order of input items.",
    ),
]


def build_callback(sub_command):
    def callback(pipeline, autocall, **kwargs):
        if autocall:
            howcall = interpret.HowCall.SINGLE
        else:
            howcall = interpret.HowCall.NONE

        return [
            {
                "name": sub_command.name.replace("-", "_"),
                "howcall": howcall,
                "pipeline": pipeline,
                **kwargs,
            }
        ]

    return callback


for subcommand in subcommands:

    subcommand.params = [
        click.Option(["--autocall/--no-autocall"], is_flag=True, default=True),
        click.Argument(["pipeline"]),
    ]
    subcommand.callback = build_callback(subcommand)
    # TODO: add_cli and add_traversal should be the non-decorator form
    registry.add_cli(name=subcommand.name)(subcommand)


@registry.add_cli(name="reduce")
@click.command(
    "reduce", short_help="Reduce a sequence with a <function>. e.g. `operator.mul`."
)
@click.argument("function_name")
def _reduce(function_name):
    return [{"pipeline": f"toolz.curry({function_name})", "name": "reduce"}]


@registry.add_cli(name="eval")
@click.command("eval", short_help="Call <pipeline> without any input.")
@click.argument("expression")
def _eval(expression):
    return [{"pipeline": expression, "name": "eval"}]
