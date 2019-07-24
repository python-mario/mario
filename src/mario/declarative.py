import typing as t

import attr
import click
import marshmallow
import pyrsistent
from marshmallow import fields


TYPES = {t.__name__: t for t in [int, str, bool, float]}


def get_jsonschema_type_mapping(type_):
    def _jsonschema_type_mapping(self):
        d = {"type": type_}

        if "description" in self.metadata.keys():
            d["description"] = self.metadata["description"]
        else:
            d["description"] = self.metadata["metadata"]["description"]

        return d

    return _jsonschema_type_mapping


class TypeField(marshmallow.fields.Field):
    def __init__(self, *args, **kwargs):
        self.default = kwargs.get("default", marshmallow.missing)
        super().__init__(*args, **kwargs)

    # pylint: disable=redefined-outer-name
    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return TYPES[value]
        except KeyError:
            if self.default == marshmallow.missing:
                raise
            return self.default

    _jsonschema_type_mapping = get_jsonschema_type_mapping("string")


class OptionNameField(marshmallow.fields.Field):
    # pylint: disable=redefined-outer-name
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]

    _jsonschema_type_mapping = get_jsonschema_type_mapping("string")


class ArgumentNameField(marshmallow.fields.Field):
    # pylint: disable=redefined-outer-name
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]

    _jsonschema_type_mapping = get_jsonschema_type_mapping("string")


class AnyField(marshmallow.fields.Field):
    _jsonschema_type_mapping = get_jsonschema_type_mapping("string")


class OptionSchema(marshmallow.Schema):
    """A command line named option for a new command."""

    param_decls = OptionNameField(
        data_key="name",
        metadata={"description": "Name of the option. Usually prefixed with - or --."},
    )
    type = TypeField(
        metadata={"description": f'Name of the type. {", ".join(TYPES)} accepted.'}
    )
    is_flag = fields.Boolean(
        default=False, metadata={"description": "Whether the option is a boolean flag."}
    )
    help = fields.String(
        default=None, metadata={"description": "Documentation for the option."}
    )
    hidden = fields.Boolean(
        default=False,
        metadata={"description": "Whether the option is hidden from help."},
    )
    required = fields.Boolean(
        default=False, metadata={"description": "Whether the option is required."}
    )
    nargs = fields.Integer(
        metadata={"description": "Number of instances expected. Pass -1 for variadic."}
    )
    multiple = fields.Boolean(
        metadata={"description": "Whether multiple values can be passed."}
    )
    default = AnyField(default=None, metadata={"description": "Default value."})
    choices = fields.List(
        fields.String(),
        metadata={"description": "List of allowed string values."},
        default=None,
    )

    @marshmallow.post_load()
    def make_option(self, validated, partial, many):  # pylint: disable=unused-argument
        choices = validated.pop("choices", None)
        if choices:
            validated["type"] = click.Choice(choices)
        return click.Option(**validated)


class ArgumentSchema(marshmallow.Schema):
    """A command-line positional argument for a new command."""

    param_decls = ArgumentNameField(
        data_key="name", metadata={"description": "Name of the argument."}
    )
    type = TypeField(
        default=str,
        metadata={"description": f'Name of the type. {", ".join(TYPES)} accepted.'},
    )
    required = fields.Boolean(
        default=True, metadata={"description": "Whether the argument is required."}
    )
    nargs = fields.Integer(
        default=None,
        metadata={"description": "Number of instances expected. Pass -1 for variadic."},
    )
    choices = fields.List(
        fields.String(),
        metadata={"description": "List of allowed string values."},
        default=None,
    )

    @marshmallow.post_load()
    def make_argument(
        self, validated, partial, many
    ):  # pylint: disable=unused-argument
        choices = validated.pop("choices", None)
        if choices:
            validated["type"] = click.Choice(choices)
        return click.Argument(**validated)


@attr.dataclass(frozen=True)
class RemapParam:
    new: str
    old: str


class RemapParamSchema(marshmallow.Schema):
    """Translation between the name of a base command's parameter and the name of the new command's parameter."""

    new = fields.String(metadata={"description": "New name of the parameter."})
    old = fields.String(metadata={"description": "Old name of the parameter."})

    @marshmallow.post_load()
    def make_remap(self, validated, partial, many):  # pylint: disable=unused-argument
        return RemapParam(**validated)


@attr.dataclass(frozen=True)
class CommandStage:
    command: str
    remap_params: t.List[RemapParam] = attr.ib(converter=pyrsistent.freeze)
    params: t.Dict[str, str] = attr.ib(converter=pyrsistent.freeze)


class CommandStageSchema(marshmallow.Schema):
    """A single stage of a new command pipeline."""

    command = fields.String(metadata={"description": "Name of the base command"})
    remap_params = fields.List(
        fields.Nested(RemapParamSchema),
        missing=list,
        metadata={
            "description": "Provide new names for the parameters, different from the base command parameters' names"
        },
    )
    params = fields.Dict(
        missing=dict,
        metadata={
            "description": "Mapping from new command param name (str) to value (any json type)."
        },
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):  # pylint: disable=unused-argument
        return CommandStage(**validated)


@attr.dataclass(frozen=True)
class CommandTest:
    invocation: t.List[str] = attr.ib(converter=pyrsistent.freeze)
    input: str
    output: str


class CommandTestSchema(marshmallow.Schema):
    """A test of a new command."""

    invocation = fields.List(
        fields.String(),
        metadata={
            "description": "Command line arguments to mario. (Don't include `mario`.)"
        },
    )
    input = fields.String(
        metadata={"description": "String passed on stdin to the program."}
    )
    output = fields.String(
        metadata={"description": "Expected string output from the program."}
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):  # pylint: disable=unused-argument
        return CommandTest(**validated)


@attr.dataclass(frozen=True)
class CommandSpec:
    name: str
    short_help: t.Optional[str]
    help: t.Optional[str]
    arguments: t.List[click.Argument] = attr.ib(converter=pyrsistent.freeze)
    options: t.List[click.Option] = attr.ib(converter=pyrsistent.freeze)
    stages: t.List[CommandStage] = attr.ib(converter=pyrsistent.freeze)
    inject_values: t.List[str] = attr.ib(converter=pyrsistent.freeze)
    tests: t.List[CommandTest] = attr.ib(converter=pyrsistent.freeze)
    section: str
    hidden: bool


class CommandSpecSchema(marshmallow.Schema):
    """A new command."""

    name = fields.String(metadata={"description": "Name of the new command."})
    help = fields.String(
        default=None,
        missing=None,
        metadata={
            "description": "Long-form documentation of the command. Will be interpreted as ReStructuredText markup."
        },
    )
    short_help = fields.String(
        default=None,
        missing=None,
        metadata={"description": "Single-line CLI description."},
    )
    arguments = fields.List(
        fields.Nested(ArgumentSchema),
        missing=list,
        metadata={"description": "Arguments accepted by the new command."},
    )
    options = fields.List(
        fields.Nested(OptionSchema),
        missing=list,
        metadata={"description": "Options accepted by the new command."},
    )
    stages = fields.List(
        fields.Nested(CommandStageSchema),
        metadata={
            "description": "List of pipeline command stages that input will go through."
        },
    )
    inject_values = fields.List(
        fields.String(),
        missing=list,
        metadata={
            "description": (
                "CLI parameters to be injected into the local namespace, accessible by the executing commands."
            )
        },
    )
    tests = fields.List(
        fields.Nested(CommandTestSchema),
        missing=list,
        data_key="tests",
        metadata={"description": "List of specifications to test the new command."},
    )
    section = fields.String(
        missing=None,
        metadata={
            "description": "Name of the documentation section in which the new command should appear."
        },
    )
    hidden = fields.Boolean(
        missing=False, metadata={"description": "Hide this command on the help page."}
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):  # pylint: disable=unused-argument
        return CommandSpec(**validated)
