import textwrap

import click

import mario.doc


class CommandInSection(click.Command):
    def __init__(self, *args, section=None, **kwargs):
        self.section = section
        super().__init__(*args, **kwargs)


class ReSTCommand(click.Command):
    """Parse help as rst."""

    def format_help_text(self, ctx, formatter):

        if self.help:
            self.help = mario.doc.rst2text(textwrap.dedent(self.help))
            original_wrap_text = click.formatting.wrap_text
            click.formatting.wrap_text = lambda x, *a, **kw: x
            super().format_help_text(ctx, formatter)
            click.formatting.wrap_text = original_wrap_text

        elif self.short_help:
            original_help = self.help
            self.help = self.short_help
            super().format_help_text(ctx, formatter)
            self.help = original_help


class DocumentedCommand(ReSTCommand, CommandInSection):
    pass
