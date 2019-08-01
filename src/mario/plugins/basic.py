import subprocess
import sys

import click

from mario import cli_tools
from mario import doc
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
async def map(
    function, items, exit_stack, max_concurrent
):  # pylint: disable=redefined-builtin
    """
    Run code on each input item.

    Each item is handled in the order it was received, and also output in the
    same order. For less strict ordering and asynchronous execution, see
    ``async-map`` and ``async-map-unordered``.

    For example,

    .. code-block:: bash

        $ mario map 'x*2' <<EOF
        a
        b
        c
        EOF
        aa
        bb
        cc

    """
    return await exit_stack.enter_async_context(
        traversals.sync_map(function, items, max_concurrent)
    )


@registry.add_traversal("async_map", calculate_more_params=calculate_function)
async def async_map(function, items, exit_stack, max_concurrent):
    """
    Run code on each input item asynchronously.

    The order of inputs is retained in the outputs. However, the order of inputs
    does not determine the order in which each input is handled, only the order
    in which its result is emitted. To keep the order in which each input is
    handled, use the synchronous version, ``map``.

    In this example, we make requests that have a server-side delay of specified
    length. The input order is retained in the output by holding each item until
    its precedents are ready.

    .. code-block:: bash


           $ mario async-map 'await asks.get ! x.json()["url"]'  <<EOF
           http://httpbin.org/delay/5
           http://httpbin.org/delay/1
           http://httpbin.org/delay/2
           http://httpbin.org/delay/3
           http://httpbin.org/delay/4
           EOF
           https://httpbin.org/delay/5
           https://httpbin.org/delay/1
           https://httpbin.org/delay/2
           https://httpbin.org/delay/3
           https://httpbin.org/delay/4

    """
    return await exit_stack.enter_async_context(
        traversals.async_map(function, items, max_concurrent)
    )


@registry.add_traversal("async_map_unordered", calculate_more_params=calculate_function)
async def async_map_unordered(function, items, exit_stack, max_concurrent):
    """
    Run code on each input item asynchronously, without retaining input order.

    Each result is emitted in the order it becomes ready, regardless of input
    order. Input order is also ignored when determining in which order to
    *start* handling each item. Results start emitting as soon as the first one
    is ready. It also saves memory because it doesn't require accumulating
    results while waiting for previous items to become ready. For stricter
    ordering, see ``map`` or ``async_map``.

    In this example, we make requests that have a server-side delay of specified
    length. The input order is lost but the results appear immediately as they
    are ready (the delay length determines the output order):

    .. code-block:: bash

           $ mario async-map-unordered 'await asks.get ! x.json()["url"]'  <<EOF
           http://httpbin.org/delay/5
           http://httpbin.org/delay/1
           http://httpbin.org/delay/2
           http://httpbin.org/delay/3
           http://httpbin.org/delay/4
           EOF
           https://httpbin.org/delay/1
           https://httpbin.org/delay/2
           https://httpbin.org/delay/3
           https://httpbin.org/delay/4
           https://httpbin.org/delay/5

    """
    return await exit_stack.enter_async_context(
        traversals.async_map_unordered(function, items, max_concurrent)
    )


@registry.add_traversal("filter", calculate_more_params=calculate_function)
async def filter(
    function, items, exit_stack, max_concurrent
):  # pylint: disable=redefined-builtin
    """
    Keep input items that satisfy a condition.

    Order of input items is retained in the output.

    For example,

    .. code-block::

        $ mario filter 'x > "c"' <<EOF
        a
        b
        c
        d
        e
        f
        EOF
        d
        e
        f
    """

    return await exit_stack.enter_async_context(
        traversals.sync_filter(function, items, max_concurrent)
    )


@registry.add_traversal("async_filter", calculate_more_params=calculate_function)
async def async_filter(function, items, exit_stack, max_concurrent):
    """
    Keep input items that satisfy an asynchronous condition.

    For example,

    .. code-block:: bash

        $ mario async-filter 'await asks.get(x).json()["url"].endswith(("1", "3"))'  <<EOF
        http://httpbin.org/delay/5
        http://httpbin.org/delay/1
        http://httpbin.org/delay/2
        http://httpbin.org/delay/3
        http://httpbin.org/delay/4
        EOF
        http://httpbin.org/delay/1
        http://httpbin.org/delay/3

    """
    return await exit_stack.enter_async_context(
        traversals.async_filter(function, items, max_concurrent)
    )


@registry.add_traversal("apply", calculate_more_params=calculate_function)
async def apply(function, items):
    """
    Apply code to the iterable of items.

    The code should take an iterable and it will be called with the input items.
    The items iterable will be converted to a list before the code is called, so
    it doesn't work well on very large streams.

    For example,

    .. code-block:: bash

        $ mario map int apply sum <<EOF
        10
        20
        30
        EOF
        60

    """
    return traversals.AsyncIterableWrapper([await function([x async for x in items])])


@registry.add_traversal("async_apply", calculate_more_params=calculate_function)
async def async_apply(function, items):
    """Apply code to an async iterable of items.

    The code should take an async iterable.
    """
    return await traversals.async_apply(function, items)


# pylint: disable=redefined-builtin
@registry.add_traversal(
    "eval",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def eval(function):
    """
    Evaluate a Python expression.

    No input items are used.

    For example,

    .. code-block:: bash

        $ mario eval 1+1
        2
    """
    return traversals.AsyncIterableWrapper([await function(None)])


@registry.add_traversal("reduce", calculate_more_params=calculate_reduce)
async def reduce(function, items, exit_stack, max_concurrent):
    """
    Reduce input items with code that takes two arguments, similar to ``functools.reduce``.

    For example,

    .. code-block:: bash

        $ mario reduce map int operator.mul <<EOF
        1
        2
        3
        4
        5
        EOF
        120

    """
    return await exit_stack.enter_async_context(
        traversals.async_reduce(function, items, max_concurrent)
    )


@registry.add_traversal(
    "chain",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def chain(items, exit_stack):
    """
    Concatenate a sequence of input iterables together into one long iterable.

    Converts an iterable of iterables of items into an iterable of items, like `itertools.chain.from_iterable <https://docs.python.org/3/library/itertools.html#itertools.chain.from_iterable>`_.

    For example,

    .. code-block:: bash

        $ mario eval '[[1,2]]'
        [[1, 2]]


        $ mario eval '[[1, 2]]' chain
        [1, 2]

    """
    return await exit_stack.enter_async_context(traversals.sync_chain(items))


@registry.add_traversal(
    "async-chain",
    calculate_more_params=lambda x: calculate_function(
        x, howcall=interpret.HowCall.NONE
    ),
)
async def async_chain(items, exit_stack):
    """
    Concatenate a sequence of input async iterables into one long async iterable.

    Converts an async iterable of async iterables of items into an async
    iterable of items, like `itertools.chain.from_iterable <https://docs.python.org/3/library/itertools.html#itertools.chain.from_iterable>`_
    for async iterables.

    """
    return await exit_stack.enter_async_context(traversals.async_chain(items))


subcommands = [
    cli_tools.DocumentedCommand(
        "map",
        help=map.__doc__,
        short_help="Call code on each line of input.",
        section="Traversals",
    ),
    cli_tools.DocumentedCommand(
        "async-map",
        help=async_map.__doc__,
        short_help="Call code on each line of input.",
        section="Async traversals",
    ),
    cli_tools.DocumentedCommand(
        "apply",
        help=apply.__doc__,
        short_help="Call code on input as a sequence.",
        section="Traversals",
    ),
    cli_tools.DocumentedCommand(
        "async-apply",
        help=async_apply.__doc__,
        short_help="Call code asynchronously on input as a sequence.",
        section="Async traversals",
    ),
    cli_tools.DocumentedCommand(
        "filter",
        help=filter.__doc__,
        short_help="Call code on each line of input and exclude false values.",
        section="Traversals",
    ),
    cli_tools.DocumentedCommand(
        "async-filter",
        help=async_filter.__doc__,
        short_help="Async call code on each line of input and exclude false values.",
        section="Async traversals",
    ),
    cli_tools.DocumentedCommand(
        "async-map-unordered",
        help=async_map_unordered.__doc__,
        short_help="Call code on each line of input, ignoring order of input items.",
        section="Async traversals",
    ),
    cli_tools.DocumentedCommand(
        "eval",
        help=eval.__doc__,
        short_help="Evaluate a python expression code",
        section="Traversals",
    ),
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
        click.Option(
            ["--autocall/--no-autocall"],
            is_flag=True,
            default=True,
            help='Automatically call the function if "x" does not appear in the expression. '
            "Allows ``map len`` instead of ``map len(x)``.",
        ),
        click.Argument(["code"]),
    ]
    subcommand.callback = build_callback(subcommand)
    subcommand = option_exec_before(subcommand)
    # pylint: disable=fixme
    # TODO: add_cli and add_traversal should be the non-decorator form
    registry.add_cli(name=subcommand.name)(subcommand)


@registry.add_cli(name="reduce")
@click.command(  # type: ignore
    "reduce",
    cls=cli_tools.DocumentedCommand,
    section="Traversals",
    short_help="Reduce a sequence with a function like ``operator.mul``.",
    help=reduce.__doc__,
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
    cli_tools.DocumentedCommand(
        "chain",
        callback=lambda **kw: [{"name": "chain", "parameters": kw}],
        help=chain.__doc__,
        short_help="Expand iterable of iterables of items into an iterable of items.",
        section="Traversals",
    ),
    cli_tools.DocumentedCommand(
        "async-chain",
        callback=lambda **kw: [{"name": "async-chain", "parameters": kw}],
        short_help="Expand iterable of async iterables into an iterable of items.",
        help=async_chain.__doc__,
        section="Async traversals",
    ),
]
for cmd in more_commands:
    registry.add_cli(name=cmd.name)(cmd)


meta = click.Group("meta", chain=True)
meta.section = doc.UNSECTIONED  # type: ignore
meta.sections = None  # type: ignore
meta.help = "Commands about using mario."


@meta.command(
    context_settings=dict(ignore_unknown_options=True),
    cls=cli_tools.DocumentedCommand,
    section=doc.UNSECTIONED,
)
@click.argument("pip_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def pip(ctx, pip_args):
    """
    Run ``pip`` in the environment that mario is installed into.

    Arguments are forwarded to ``pip``.
    """
    cli_args = [sys.executable, "-m", "pip"] + list(pip_args)
    ctx.exit(subprocess.run(cli_args).returncode)


@meta.command(
    "test",
    cls=cli_tools.DocumentedCommand,
    section=doc.UNSECTIONED,
    context_settings=dict(ignore_unknown_options=True),
)
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def run_tests(ctx, pytest_args):
    """
    Run all declarative command tests from plugins and config.

    Executes each test in the ``command.tests`` field with pytest.

    Default pytest args: ``-vvv --tb=short``
    """

    import tempfile
    import textwrap

    pytest_args = list(pytest_args) or ["-vvv", "--tb=short"]

    source = textwrap.dedent(
        """\
    import subprocess
    import sys

    import pytest

    import mario.app

    COMMANDS = mario.app.global_registry.commands.values()  # pylint: disable=no-member
    TEST_SPECS = [test for command in COMMANDS for test in command.tests]


    @pytest.mark.parametrize(\"test_spec\", TEST_SPECS, ids=lambda ts: str(list(ts.invocation)))
    def test_command(test_spec):

        output = subprocess.check_output(
            [sys.executable, \"-m\", \"mario\"] + list(test_spec.invocation),
            input=test_spec.input.encode(),
        ).decode()
        assert output == test_spec.output

    """
    )
    f = tempfile.NamedTemporaryFile("wt", suffix=".py", delete=False)
    f.write(source)
    f.close()
    args = [sys.executable, "-m", "pytest"] + pytest_args + [f.name]
    proc = subprocess.run(args)
    ctx.exit(proc.returncode)


registry.add_cli(name="meta")(meta)
