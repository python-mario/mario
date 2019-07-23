import click

import mario.doc


class CommandInSection(click.Command):
    def __init__(self, *args, section=None, **kwargs):
        self.section = section
        super().__init__(*args, **kwargs)
