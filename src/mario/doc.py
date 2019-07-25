from __future__ import annotations

import types
import typing as t

import attr


def parse_rst(text: str) -> docutils.nodes.document:  # type: ignore
    import docutils.nodes
    import docutils.parsers.rst
    import docutils.utils

    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components
    ).get_default_values()
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


# pylint: disable=undefined-variable
def format_text(document: docutils.nodes.document) -> str:  # type: ignore
    import sphinx.builders.text
    import sphinx.events
    import sphinx.util.osutil
    import sphinx.writers.text

    app = types.SimpleNamespace(
        srcdir=None,
        confdir=None,
        outdir=None,
        doctreedir="/",
        config=types.SimpleNamespace(
            text_newlines="native",
            text_sectionchars="=",
            text_add_secnumbers=False,
            text_secnumber_suffix=".",
        ),
        tags=set(),
        events=sphinx.events.EventManager(),
        registry=types.SimpleNamespace(
            create_translator=lambda self, something, new_builder: sphinx.writers.text.TextTranslator(
                document, new_builder
            )
        ),
    )

    builder = sphinx.builders.text.TextBuilder(app)

    translator = sphinx.writers.text.TextTranslator(document, builder)
    document.walkabout(translator)
    return translator.body


def rst2text(source: str) -> str:
    document = parse_rst(source)
    return format_text(document)


@attr.dataclass(frozen=True)
class HelpSection:
    priority: int
    entries: t.List[str]
    doc: str = ""
    name: t.Optional[str] = None


@attr.dataclass(frozen=True)
class HelpSectionSpec:
    priority: int
    doc: str = ""
    name: str = ""


UNSECTIONED = "UNSECTIONED"
UNSECTIONED_PRIORITY = 100_000

SECTION_SPECS = {
    HelpSectionSpec(
        name="Traversals", doc="Commands for calling code on data.", priority=0
    ),
    HelpSectionSpec(
        name="Async traversals",
        doc="Commands for asynchronously calling code on data.",
        priority=1,
    ),
    HelpSectionSpec(name=UNSECTIONED, doc="", priority=UNSECTIONED_PRIORITY),
}

SECTION_NAME_TO_SECTION_SPEC = {s.name: s for s in SECTION_SPECS}

DEFAULT_SECTION_PRIORITY = 500

NULL_SECTION = HelpSectionSpec(
    priority=1000, name="Custom", doc="Custom defined commands"
)
