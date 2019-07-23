import importlib


sphinx_jsonschema = importlib.import_module("sphinx-jsonschema")

_glob_app = None


class DefinitionWideFormat(sphinx_jsonschema.wide_format.WideFormat):  # type: ignore
    """Add definition field."""

    def _objecttype(self, schema):
        # create description and type rows
        rows = self._simpletype(schema)
        rows.extend(self._objectproperties(schema, "definition"))
        rows.extend(self._objectproperties(schema, "properties"))
        rows.extend(self._objectproperties(schema, "patternProperties"))
        rows.extend(self._bool_or_object(schema, "additionalProperties"))
        rows.extend(self._kvpairs(schema, self.KV_OBJECT))
        return rows

    def _dispatch(self, schema, label=None):
        # Main driver of the recursive schema traversal.
        rows = []
        # pylint: disable=no-member
        self.nesting += 1

        if "type" in schema:
            # select processor for type
            if "object" in schema["type"]:
                rows = self._objecttype(schema)
            elif "array" in schema["type"]:
                rows = self._arraytype(schema)
            else:
                rows = self._simpletype(schema)
        else:
            if "description" in schema:
                rows.append(self._line(self._cell(schema["description"])))

        if "$ref" in schema:
            rows.append(
                self._line(
                    self._cell(
                        (":ref:`" + schema["$ref"] + "`").replace("#/definitions/", "")
                    )
                )
            )

        for k in self.COMBINATORS:
            # combinators belong at this level as alternative to type
            if k in schema:
                items = []
                for s in schema[k]:
                    items.extend(self._dispatch(s, self._cell("-")))
                rows.extend(self._prepend(self._cell(k), items))

        for k in self.SINGLEOBJECTS:
            # combinators belong at this level as alternative to type
            if k in schema:
                rows.extend(self._dispatch(schema[k], self._cell(k)))

        # definitions aren't really type equiv's but still best place for them
        rows.extend(self._objectproperties(schema, "definitions"))

        if label is not None:
            # prepend label column if required
            rows = self._prepend(label, rows)

        # pylint: disable=no-member
        self.nesting -= 1
        return rows


class DefinitionJsonSchema(sphinx_jsonschema.JsonSchema):  # type: ignore
    def run(self):
        # pylint: disable=redefined-builtin
        # pylint: disable=protected-access
        format = DefinitionWideFormat(
            self.state, self.lineno, sphinx_jsonschema._glob_app
        )
        return format.transform(self.schema)


def setup(app):

    global _glob_app  # pylint: disable=global-statement
    _glob_app = app
    app.add_directive("jsonschema", DefinitionJsonSchema)
