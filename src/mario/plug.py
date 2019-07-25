import importlib
import importlib.resources
import importlib.util
import inspect
import sys
import types
import typing as t
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List

import attr
import importlib_metadata
import toml

from mario import config
from mario import declarative


@attr.dataclass
class PluginObject:
    name: str
    traversal_function: types.FunctionType
    required_parameters: List[str]
    calculate_more_params: types.FunctionType = attr.ib(default=lambda x: {})


@attr.dataclass
class CommandStage:
    name: str

    options: List[str]
    arguments: List[str]
    remap_params: Dict


@attr.dataclass
class CommandCommand:
    name: str
    components: List[CommandStage]
    short_help: str
    options: t.Dict = attr.ib(factory=dict)
    arguments: t.Dict = attr.ib(factory=dict)


@attr.s(repr=False)
class _NoDefaultType:
    def __repr__(self):
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefaultType()


@attr.dataclass
class GlobalOption:
    name: str
    type: t.Type
    default: _NoDefaultType


@attr.s
class Registry:
    traversals: Dict[str, PluginObject] = attr.ib(factory=dict)
    global_options: Dict[str, GlobalOption] = attr.ib(factory=dict)
    cli_functions: Dict[str, Any] = attr.ib(factory=dict)
    commands: Dict[str, CommandCommand] = attr.ib(factory=dict)

    def register(self, name=None, params=None):
        def wrap(function):
            if name is None:
                registered_name = function.__name__
            else:
                registered_name = name

            # pylint: disable=unsupported-assignment-operation
            self.traversals[registered_name] = PluginObject(
                registered_name, function, params
            )
            return function

        return wrap

    def add_traversal(self, name=None, calculate_more_params=lambda x: {}):
        def wrap(function):

            if name is None:
                registered_name = function.__name__
            else:
                registered_name = name

            params = [param for param in inspect.signature(function).parameters.keys()]
            # pylint: disable=unsupported-assignment-operation
            self.traversals[
                registered_name
            ] = PluginObject(  # pylint: disable=unsupported-assignment-operation
                registered_name, function, params, calculate_more_params
            )
            return function

        return wrap

    def add_cli(self, name=None):
        def wrap(function):
            if name is None:
                registered_name = getattr(function, "__name__", None), function.name
            else:
                registered_name = name
            # pylint: disable=unsupported-assignment-operation
            self.cli_functions[registered_name] = function

            return function

        return wrap


def plugin_module_paths() -> List[str]:
    return [
        entry_point.value + "." + entry_point.name
        for entry_point in importlib_metadata.entry_points()["mario_plugins"]
    ]


def collect_modules(import_paths: Iterable[str]) -> List[types.ModuleType]:
    modules = []
    for path in import_paths:
        modules.append(importlib.import_module(path))
    return modules


def combine_registries(registries):
    global_options = {}
    traversals = {}
    cli_functions = {}
    commands = {}
    for registry in registries:
        traversals.update(registry.traversals)
        global_options.update(registry.global_options)
        cli_functions.update(registry.cli_functions)
        commands.update(registry.commands)
    return Registry(traversals, global_options, cli_functions, commands)


def make_plugin_registry():
    plugin_modules = collect_modules(plugin_module_paths())
    plugin_registries = [module.registry for module in plugin_modules]

    return combine_registries(plugin_registries)


def make_config_registry():
    sys.path.append(str(config.get_config_dir()))

    try:
        # pylint: disable=import-error
        import m
    except ModuleNotFoundError:
        return Registry()

    return getattr(m, "registry", None) or Registry()


def make_global_registry():
    return combine_registries(
        [
            make_plugin_registry(),
            make_config_registry(),
            make_config_commands_registry(),
            make_plugin_commands_registry(),
        ]
    )


def make_commands(conf):

    commands = declarative.CommandSpecSchema(many=True).load(conf.get("command", []))

    return commands


def make_config_commands_registry():
    conf = config.load_config()

    commands = make_commands(conf)
    return Registry(commands={c.name: c for c in commands})


def make_plugin_commands_registry(package="mario.plugins"):
    plugin_tomls = [
        filename
        for filename in importlib.resources.contents(package)
        if filename.endswith(".toml")
    ]
    confs = [
        toml.loads(importlib.resources.read_text(package, filename))
        for filename in plugin_tomls
    ]

    conf_command_groups = [make_commands(conf) for conf in confs]
    registries = [
        Registry(commands={c.name: c for c in commands})
        for commands in conf_command_groups
    ]
    return combine_registries(registries)
