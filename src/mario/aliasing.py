import typing as t

import attr
import click
import marshmallow
from marshmallow import fields


TYPES = {t.__name__: t for t in [int, str, bool, float]}


class TypeField(marshmallow.fields.Field):
    def __init__(self, *args, **kwargs):
        self.default = kwargs.get("default", marshmallow.missing)
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return TYPES[value]
        except KeyError:
            if self.default == marshmallow.missing:
                raise
            return self.default


class OptionNameField(marshmallow.fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]
        if not value.startswith("-"):
            raise marshmallow.ValidationError(
                f'{value} is an option, so must start with "-".'
            )
        return [value]


class ArgumentNameField(marshmallow.fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        return [value]


class OptionSchema(marshmallow.Schema):
    param_decls = OptionNameField(data_key="name")
    type = TypeField()
    is_flag = fields.Boolean(default=False)
    help = fields.String(default=None)
    hidden = fields.Boolean(default=False)
    required = fields.Boolean(default=False)
    nargs = fields.Integer()
    multiple = fields.Boolean()
    default = fields.Field(default=None)

    @marshmallow.post_load()
    def make_option(self, validated, partial, many):
        return click.Option(**validated)


class ArgumentSchema(marshmallow.Schema):
    param_decls = ArgumentNameField(data_key="name")
    type = TypeField()
    required = fields.Boolean()
    nargs = fields.Integer()

    @marshmallow.post_load()
    def make_argument(self, validated, partial, many):
        return click.Argument(**validated)


@attr.dataclass
class RemapParam:
    new: str
    old: str


class RemapParamSchema(marshmallow.Schema):
    new = fields.String()
    old = fields.String()

    @marshmallow.post_load()
    def make_remap(self, validated, partial, many):
        return RemapParam(**validated)


@attr.dataclass
class AliasStage:
    command: str
    remap_params: t.List[RemapParam]
    options: t.Dict[str, str]
    arguments: t.List[str]


class AliasStageSchema(marshmallow.Schema):
    command = fields.String()
    remap_params = fields.List(fields.Nested(RemapParamSchema), missing=list)
    arguments = fields.List(fields.String(), missing=list)
    options = fields.Dict(missing=list)

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return AliasStage(**validated)


@attr.dataclass
class AliasTestSpec:
    invocation: t.List[str]
    input: str
    output: str


class AliasTestSpecSchema(marshmallow.Schema):
    invocation = fields.List(fields.String())
    input = fields.String()
    output = fields.String()

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return AliasTestSpec(**validated)


@attr.dataclass
class Alias:
    name: str
    short_help: t.Optional[str]
    help: t.Optional[str]
    arguments: t.List[click.Argument]
    options: t.List[click.Option]
    stages: t.List[AliasStage]
    inject_values: t.List[str]
    test_specs: t.List[AliasTestSpec]


class AliasSchema(marshmallow.Schema):
    name = fields.String()
    help = fields.String(default=None, missing=None)
    short_help = fields.String(default=None, missing=None)
    arguments = fields.List(fields.Nested(ArgumentSchema), missing=list)
    options = fields.List(fields.Nested(OptionSchema), missing=list)
    stages = fields.List(fields.Nested(AliasStageSchema), data_key="stage")
    inject_values = fields.List(fields.String(), missing=list)
    test_specs = fields.List(
        fields.Nested(AliasTestSpecSchema), missing=list, data_key="test_spec"
    )

    @marshmallow.post_load()
    def make(self, validated, partial, many):
        return Alias(**validated)
