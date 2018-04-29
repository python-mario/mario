# !/usr/bin/env python

from __future__ import generator_stop

from pprint import pprint

import importlib
import itertools
import os
import re
import sys
import token
import io
from tokenize import tokenize, untokenize

import attr
import click
import toolz
from twisted.internet import reactor, task
from twisted.internet.defer import Deferred, inlineCallbacks, DeferredList
from twisted.python.log import err

_PYPE_VALUE = '__PYPE_VALUE_'


class PypeException(Exception):
    pass


class PypeParseError(PypeException):
    pass


def _is_name_token(token_object):
    return token.tok_name[token_object.type] == 'NAME'


def _is_reference_part(token_object):
    if _is_name_token(token_object):
        return True
    if token_object.string == '.':
        return True
    return False


def _string_to_tokens(string):
    bytestring = string.encode('utf-8')
    bytesio = io.BytesIO(bytestring)
    tokens = tokenize(bytesio.readline)
    return tokens


def _tokens_to_string(token_objects):
    """Untokenize, ignoring whitespace."""
    return ''.join(t.string for t in token_objects)


def _get_maybe_namespaced_identifiers(string):
    scanner = _StringScanner(string)
    return scanner.scan()


@attr.s
class _StringScanner:

    _string = attr.ib()
    _current_tokens = attr.ib(default=attr.Factory(list))
    _identifier_strings = attr.ib(default=attr.Factory(set))

    def _maybe_update(self):
        if self._current_tokens and _is_name_token(self._current_tokens[-1]):
            if _is_name_token(self._current_tokens[0]):
                self._identifier_strings.add(
                    _tokens_to_string(self._current_tokens))
            self._current_tokens = []

    def scan(self):
        tokens = _string_to_tokens(self._string)

        for token_object in tokens:
            if _is_reference_part(token_object):
                self._current_tokens.append(token_object)
                continue
            self._maybe_update()

        self._maybe_update()

        return self._identifier_strings


def _get_named_module(name):
    builtins = sys.modules['builtins']
    if hasattr(builtins, name):
        return builtins
    try:
        return importlib.import_module(name)
    except ImportError:
        pass
    raise LookupError(f'Could not find {name}')


def _get_autoimport_modules(fullname):
    name_parts = fullname.split('.')
    try_names = []
    for idx in range(len(name_parts)):
        try_names.insert(0, '.'.join(name_parts[:idx + 1]))

    for name in try_names:
        try:
            module = _get_named_module(name)
        except LookupError:
            pass
        else:
            if module is sys.modules['builtins']:
                return {}
            return {name: module}
    raise RuntimeError(f'Could not find {fullname}')


def _get_named_modules(imports):
    """Import modules into dict mapping name to module."""
    modules = {}
    for module_name in imports:
        modules[module_name] = importlib.import_module(module_name)
    return modules


def _add_short_placeholder(command_string, short_placeholder='?'):
    if short_placeholder in command_string:
        return command_string
    return f'{command_string}({short_placeholder})'


def _get_autoimports(string, separator='||'):
    components = [comp.strip() for comp in string.split(separator)]
    name_to_module = {}
    for component in components:
        identifiers = _get_maybe_namespaced_identifiers(component)
        for identifier in identifiers:
            name_module = _get_autoimport_modules(identifier)
            name_to_module.update(name_module)
    return name_to_module


def _get_modules(commands, named_imports, autoimport):
    named_modules = _get_named_modules(named_imports)
    if not autoimport:
        return named_modules
    autoimports = toolz.merge(_get_autoimports(command)
                              for command in commands)
    # named modules have priority
    modules = {**autoimports, **named_modules}
    return modules


def _maybe_add_newlines(iterator, newlines_setting='auto'):

    if newlines_setting == 'auto':
        try:
            first, iterator = toolz.peek(iterator)
        except StopIteration:
            add_newlines = False
        else:
            add_newlines = not str(first).endswith('\n')

    else:
        add_newlines = newlines_setting

    for item in iterator:
        string = str(item)
        if add_newlines:
            yield string + os.linesep
        else:
            yield string


def _check_parsing(command, placeholder):
    # TODO Fix this...
    tokens = _string_to_tokens(command)
    for tok in tokens:

        if tok.type != token.STRING:
            continue
        if placeholder not in tok.string:
            continue
        # if re.fullmatch(r'f.*\{.*%s.*\}.*' % placeholder, tok.string):
        #     continue

        other = {'$': '?', '?': '$'}[placeholder]
        raise PypeParseError(r'''

        If data should appear in quotation marks, use 'Hello, {{}}.format(?)':


            printf 'World' | pype '"Hello, {{}}!".format(?)'

            # Hello, World!


            printf 'World' | pype $'"I say, \'Hello, {{}}!\'".format(?)'

            # I say, 'Hello, World!'


        If {placeholder} should appear in quotation marks, use another placeholder:


            printf 'Is this a question' | pype --placeholder=$ '$ + "?"'

            # Is this a question?


            '''.format(placeholder=placeholder, other=other))


def run_segment(value, segment, modules):
    return eval(segment, modules, {_PYPE_VALUE: value})


def _async_do_segment(value, modules, pipeline):
    d = Deferred()
    for pipeline_segment in pipeline:
        d.addCallback(run_segment, pipeline_segment, modules)
    d.callback(value)
    return d


def _command_string_to_function(command, modules=None, symbol='?'):
    if modules is None:
        modules = {}

    command = _add_short_placeholder(command, symbol)
    command = command.replace(symbol, _PYPE_VALUE)

    def function(value):
        return eval(command, {_PYPE_VALUE: value}, modules)

    return function


def _pipestring_to_functions(multicommand_string, modules=None, symbol='?', separator='||'):
    command_strings = multicommand_string.split(separator)
    functions = []
    for command_string in command_strings:
        functions.append(_command_string_to_function(
            command_string, modules, symbol))
    return functions


def _pipestring_to_function(multicommand_string, modules=None, symbol='?', separator='||'):
    functions = _pipestring_to_functions(
        multicommand_string, modules, symbol, separator)
    return toolz.compose(*reversed(functions))


def _async_do_item(mapper_functions, item):
    d = Deferred()
    for function in mapper_functions:
        d.addCallback(function)
    d.addCallbacks(print, err)
    d.callback(item)
    return d


def _async_react_map(reactor, mapper_functions, items):
    running = [0]
    finished = Deferred()

    def check(result):
        running[0] -= 1
        if not running[0]:
            finished.callback(None)
        return result

    def wrap(it):
        for d in it:
            running[0] += 1
            d.addBoth(check)

    deferreds = (_async_do_item(mapper_functions, item) for item in items)
    wrap(deferreds)

    return finished


def _async_run(
        mapper,
        applier=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        autoimport=True,
        newlines='auto',
        reactor=reactor,
):

    commands = (x for x in [mapper] if x)
    modules = _get_modules(commands, imports, autoimport)
    mapper_functions = _pipestring_to_functions(mapper, modules, placeholder)

    task.react(_async_react_map, [mapper_functions, in_stream])


def run(  # pylint: disable=too-many-arguments
        mapper=None,
        applier=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        autoimport=True,
        newlines='auto',
):
    pipestrings = (x for x in [mapper, applier] if x)
    modules = _get_modules(pipestrings, imports, autoimport)

    items = in_stream

    if mapper:
        mapper_function = _pipestring_to_function(mapper, modules, placeholder)
        items = map(mapper_function, items)

    if applier:
        apply_function = _pipestring_to_function(applier, modules, placeholder)
        items = apply_function(items)

    items = _maybe_add_newlines(items, newlines)

    for item in items:
        yield item


def main(  # pylint: disable=too-many-arguments
        mapper=None,
        applier=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        autoimport=True,
        newlines='auto',
        do_async=False,
        reactor=reactor,
):

    if mapper:
        _check_parsing(mapper, placeholder)

    if do_async:
        _async_run(
            mapper=mapper,
            in_stream=in_stream,
            imports=imports,
            placeholder=placeholder,
            autoimport=autoimport,
            newlines=newlines,
            reactor=reactor,
        )
        sys.exit()

    else:
        gen = run(
            mapper=mapper,
            applier=applier,
            in_stream=in_stream,
            imports=imports,
            placeholder=placeholder,
            autoimport=autoimport,
            newlines=newlines,
        )

    return gen


@click.group(chain=True)
@click.option(
    '--newlines',
    '-n',
    type=click.Choice(['auto', 'yes', 'no']),
    default='auto',
    help='Add newlines.')
@click.option(
    '--autoimport/--no-autoimport',
    is_flag=True,
    default=True,
    help='Automatically import modules.')
@click.option(
    '--import',
    '-i',
    'imports',
    multiple=True,
    help='Modules to import explicitly.',
)
@click.option(
    '--placeholder',
    default='?',
    help='String to replace with data. Defaults to ?',
)
@click.option(
    '--async',
    'do_async',
    is_flag=True,
    default=False,
    help='Run commands on each input item in asynchronously.')
def cli(
        imports,
        placeholder,
        autoimport,
        newlines,
        do_async,
):
    """
    Pipe data through Python functions.

    """


def str_to_bool(string, strict=False):
    true_strings = {s: True for s in ['true', 'yes', 't', 'y']}
    false_strings = {s: False for s in ['false', 'no', 'f', 'n']}
    mapping = {
        **true_strings,
        **false_strings,
    }
    try:
        return mapping[string]
    except KeyError:
        if not strict:
            return string
        raise


@cli.resultcallback()
def process_pipeline(processors, **kwargs):

    in_stream = click.get_text_stream('stdin')

    options = dict(kwargs)
    options['newlines'] = str_to_bool(kwargs['newlines'])

    if 'do_async' in kwargs:
        options['reactor'] = reactor

    for processor in processors:
        in_stream = processor(in_stream=in_stream, **options)

    for item in in_stream:
        click.echo(item, nl=False)


@cli.command('apply')
@click.argument('applier')
def cli_apply(applier):
    def wrapped(**kwargs):
        return main(applier=applier, **kwargs)

    return wrapped


@cli.command('map')
@click.argument('mapper')
def cli_map(mapper):
    def wrapped(**kwargs):
        return main(mapper=mapper, **kwargs)

    return wrapped
