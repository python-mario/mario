from __future__ import annotations

import json
import tempfile
import traceback
import typing as t

import attr
import docutils.nodes
import docutils.parsers.rst
import docutils.parsers.rst.directives
import marshmallow
import marshmallow.fields
import marshmallow_jsonschema
import typing_extensions as te


T = t.TypeVar("T")


FIELD_MAPPING = {
    marshmallow.fields.Bool: bool,
    marshmallow.fields.Str: str,
    marshmallow.fields.Float: float,
    marshmallow.fields.Int: int,
    marshmallow.fields.List: list,
    marshmallow.fields.Mapping: dict,
    marshmallow.fields.Dict: dict,
    marshmallow.fields.Nested: object,
}


@attr.dataclass(frozen=True, slots=True)
class Table:
    title: str
    header: t.List[str]
    body: t.List[t.List[str]] = attr.ib(factory=list)
    widths: t.Union[te.Literal["auto"], t.List[int]] = "auto"


@attr.dataclass(frozen=True, slots=True)
class Field:
    name: str
    type: t.Any  # ?
    required: bool
    default: t.Any


@attr.dataclass(frozen=True, slots=True)
class SchemaSpec:
    name: str
    fields: t.List[Field]


def quote(s):
    return '"' + s + '"'


class Marshmallow3JSONSchema(marshmallow_jsonschema.JSONSchema):
    # This class fixes incompatibilities between the parent class and Marshmallow 3.
    # It also adds the `description` field.

    # pylint: disable=unused-argument
    # pylint: disable=arguments-differ
    def wrap(self, *args, many, **kwargs):
        return super().wrap(*args, **kwargs)

    def _from_python_type(self, obj, field, pytype):
        """Get schema definition from python type."""
        json_schema = {"title": field.attribute or field.data_key or field.name}

        for key, val in marshmallow_jsonschema.base.TYPE_MAP[pytype].items():
            json_schema[key] = val

        if "description" in field.metadata:
            json_schema["description"] = field.metadata["description"]

        if field.dump_only:
            json_schema["readonly"] = True

        if field.default is not marshmallow.missing:
            json_schema["default"] = field.default

        # NOTE: doubled up to maintain backwards compatibility
        metadata = field.metadata.get("metadata", {})
        metadata.update(field.metadata)

        for md_key, md_val in metadata.items():
            if md_key == "metadata":
                continue
            json_schema[md_key] = md_val

        if isinstance(field, marshmallow.fields.List):
            json_schema["items"] = self._get_schema_for_field(obj, field.inner)
        return json_schema

    def get_properties(self, obj):
        """Fill out properties field."""
        properties = {}

        for _field_name, field in sorted(obj.fields.items()):
            schema = self._get_schema_for_field(obj, field)
            properties[field.data_key or field.name] = schema

        return properties

    def get_required(self, obj):
        """Fill out required field."""
        required = []

        for _field_name, field in sorted(obj.fields.items()):
            if field.required:
                required.append(field.data_key or field.name)

        return required or marshmallow.missing

    definition = marshmallow.fields.Method("get_definition")

    def get_definition(self, obj):
        return {obj.__doc__: []}


class SchemaDirective(docutils.parsers.rst.Directive):

    has_content = False
    required_arguments = 1
    option_spec = {
        "prog": docutils.parsers.rst.directives.unchanged_required,
        "show-nested": docutils.parsers.rst.directives.flag,
        "commands": docutils.parsers.rst.directives.unchanged,
    }

    def _get_schema(self, module_path):

        # __import__ will fail on unicode,
        # so we ensure module path is a string here.
        module_path = str(module_path)

        try:
            module_name, attr_name = module_path.split(":", 1)
        except ValueError:  # noqa
            raise self.error(
                '"{}" is not of format "module:schema"'.format(module_path)
            )

        try:
            mod = __import__(module_name, globals(), locals(), [attr_name])
        except (Exception, SystemExit) as exc:  # noqa
            err_msg = 'Failed to import "{}" from "{}". '.format(attr_name, module_name)
            if isinstance(exc, SystemExit):
                err_msg += "The module appeared to call sys.exit()"
            else:
                err_msg += "The following exception was raised:\n{}".format(
                    traceback.format_exc()
                )

            raise self.error(err_msg)

        if not hasattr(mod, attr_name):
            raise self.error(
                'Module "{}" has no attribute "{}"'.format(module_name, attr_name)
            )

        schema = getattr(mod, attr_name)

        if not issubclass(schema, marshmallow.Schema):
            raise self.error(
                '"{}" of type "{}" is not derived from '
                '"marshmallow.Schema"'.format(schema, module_path)
            )
        return schema

    def _get_inner(self, field):
        if hasattr(field, "inner"):
            return self._get_inner(field.inner)

        if hasattr(field, "nested"):
            return self._get_inner(field.nested)

        return field

    def _build_section(self, schema):

        mm_json = Marshmallow3JSONSchema().dump(schema)

        # Title

        name = type(schema).__name__

        section = docutils.nodes.section(
            "",
            docutils.nodes.title(text=name),
            ids=[docutils.nodes.make_id(name)],
            names=[docutils.nodes.fully_normalize_name(name)],
        )

        # Summary

        source_name = type(schema).__name__
        result = docutils.statemachine.ViewList()

        file = tempfile.NamedTemporaryFile(mode="wt", delete=False, prefix="sphinx")

        json.dump(mm_json, file, indent=4)
        file.close()

        lines = []
        lines += [f".. jsonschema:: {file.name}\n"]

        for line in lines:
            result.append(line, source_name)

        self.state.nested_parse(result, 0, section)

        subsections = []
        for field_name in schema.fields:
            field = schema.declared_fields[field_name]
            inner = self._get_inner(field)

            if isinstance(inner, type) and issubclass(inner, marshmallow.Schema):
                subsections += self._build_section(inner())

        return [section] + subsections

    def run(self):
        # pylint: disable=attribute-defined-outside-init
        self.env = self.state.document.settings.env

        schema = self._get_schema(self.arguments[0])

        return self._build_section(schema())


def setup(app):
    app.add_directive("marshmallow", SchemaDirective)
