import sys
import textwrap
import types

import docutils.nodes
import docutils.parsers.rst
import docutils.utils
import sphinx.builders.text
import sphinx.events
import sphinx.util.osutil
import sphinx.writers.text


def parse_rst(text: str) -> docutils.nodes.document:
    parser = docutils.parsers.rst.Parser()
    components = (docutils.parsers.rst.Parser,)
    settings = docutils.frontend.OptionParser(
        components=components
    ).get_default_values()
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


def format_text(document: docutils.nodes.document) -> str:

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
