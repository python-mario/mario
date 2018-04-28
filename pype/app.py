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
import treq
from twisted.internet import reactor
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
                self._identifier_strings.add(_tokens_to_string(self._current_tokens))
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


def _make_pipeline_strings(command, placeholder, star_args=False):
    """Parse pipeline into individual components."""
    command_strings = command.split('||')
    pipeline = []
    for string in command_strings:
        string = string.strip()
        if placeholder not in string:
            string = string + '({star}{placeholder})'.format(
                star='*' if star_args else '', placeholder=placeholder)
        stage = string.replace(placeholder, _PYPE_VALUE).strip()
        pipeline.append(stage)
    return pipeline


def _get_autoimports(string):
    components = [comp.strip() for comp in string.split('||')]
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
    autoimports = toolz.merge(_get_autoimports(command) for command in commands)
    # named modules have priority
    modules = {**autoimports, **named_modules}
    return modules


def _do_command_pipeline(value, modules, pipeline):
    assert modules is not None
    for step in pipeline:
        value = eval(step, modules, {_PYPE_VALUE: value})
    return value


def _do_total(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    string = in_stream.read()
    result = _do_command_pipeline(string, modules, pipeline)
    yield result


def _do_map(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    for line in in_stream:
        result = _do_command_pipeline(line, modules, pipeline)
        yield result


def _do_reduce(command, in_stream, imports, placeholder, autoimport):

    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder, star_args=True)
    value = next(in_stream)
    for item in in_stream:
        for step in pipeline:
            value = eval(step, modules, {_PYPE_VALUE: (value, item)})
    yield value


def _maybe_add_newlines(iterator, newlines_setting='auto'):

    if newlines_setting == 'auto':
        try:
            first, iterator = toolz.peek(iterator)
        except StopIteration:
            add_newlines = False
        else:
            add_newlines = not str(first).endswith('\n')

    else:
        add_newlines = {'yes': True, 'no': False}[newlines_setting]

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


def _async_do_map(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)

    yield from (_async_do_segment(item, modules, pipeline) for item in in_stream)


def _async_do_reduce(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder, star_args=True)


# TODO make reduce async, using a function _async_do_reduce
# TODO async reduce should fire on two callbacks rather than using a DeferredList
# TODO add --nonstop option like tail -F


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
        functions.append(_command_string_to_function(command_string, modules, symbol))
    return functions


def _pipestring_to_function(multicommand_string, modules=None, symbol='?', separator='||'):
    functions = _pipestring_to_functions(multicommand_string, modules, symbol, separator)
    return toolz.compose(*reversed(functions))


# def _async_do_item(item, function):
#     d = Deferred()
#     d.addCallback(function)
#     d.addCallbacks(print, err)
#     d.callback(item)


def _do_apply(command, in_stream, imports, placeholder, autoimport):
    modules = _get_modules([command], imports, autoimport)
    pipeline = _make_pipeline_strings(command, placeholder)
    result = _do_command_pipeline(in_stream, modules, pipeline)
    return result


def _async_main(
        mapper,
        reducer=None,
        postmap=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        slurp=False,
        autoimport=True,
        newlines='auto',
        reactor=reactor,
):

    commands = (x for x in [mapper, reducer, postmap] if x)
    modules = _get_modules(commands, imports, autoimport)
    mapper_functions = _pipestring_to_functions(mapper, modules, placeholder)

    for item in in_stream:
        print(item)
        d = Deferred()
        for function in mapper_functions:
            d.addCallback(function)
        d.addCallbacks(print, err)

        d.callback(item)

    print('about to run reactor')
    reactor.run()


def main(  # pylint: disable=too-many-arguments
        mapper=None,
        reducer=None,
        postmap=None,
        in_stream=None,
        imports=(),
        placeholder='?',
        slurp=False,
        autoimport=True,
        newlines='auto',
        do_async=False,
        reactor=reactor,
        apply=None,
):
    if mapper:
        _check_parsing(mapper, placeholder)

    if do_async:
        _async_main(
            mapper=mapper,
            reducer=reducer,
            postmap=postmap,
            in_stream=in_stream,
            imports=imports,
            placeholder=placeholder,
            slurp=slurp,
            autoimport=autoimport,
            newlines=newlines,
            reactor=reactor,
        )
        sys.exit()

    commands = (x for x in [mapper, reducer, postmap, apply] if x)
    modules = _get_modules(commands, imports, autoimport)

    if apply:
        apply_function = _pipestring_to_function(apply, modules, placeholder)
        result = apply_function(in_stream)

    else:
        mapper_function = _pipestring_to_function(mapper, modules, placeholder)
        result = map(mapper_function, in_stream)

    result = _maybe_add_newlines(result, newlines)

    for item in result:
        yield item


@click.command()
@click.argument('command', default=None, required=False)
@click.argument('reducer', default=None, required=False)
@click.argument('postmap', default=None, required=False)
@click.option('--apply', default=None)
@click.option(
    '--slurp',
    '-s',
    is_flag=True,
    help='Apply function to entire input together instead of processing one line at a time.')
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
@click.option('--async', 'do_async', is_flag=True, default=False)
def cli(
        imports,
        command,
        reducer,
        placeholder,
        slurp,
        postmap,
        autoimport,
        newlines,
        do_async,
        apply,
):
    """
Pipe data through python functions.

\b
$ printf 'a.b.c\\nd.e.f\\n' |
pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || json.dumps '

\b
{"A": 1, "!": 2, "B": 1, "C": 1, "\\n": 1}
{"D": 1, "!": 2, "E": 1, "F": 1, "\\n": 1}

\b
$ printf 'aa.bbb\\n' | pype -i collections -i json 'str.replace(?, ".", "!") || str.upper || collections.Counter || {v:k for k,v in ?.items()} || json.dumps'

\b
{"2": "A", "1": "\\n", "3": "B"}

\b
$ printf 'a\\nab\\nabc\\n' | pype -i json -i toolz -i collections 'collections.Counter' 'toolz.merge_with(sum, ?)' 'json.dumps'

\b
{"a": 3, "\\n": 3, "b": 2, "c": 1}

\b
$ printf 'a\\nab\\nabc\\n' | pype -t -i json -i toolz -i collections 'collections.Counter || json.dumps'

\b
{"a": 3, "\\n": 3, "b": 2, "c": 1}


    """
    in_stream = click.get_text_stream('stdin')
    gen = main(
        command,
        reducer,
        postmap,
        in_stream,
        imports,
        placeholder,
        slurp,
        autoimport,
        newlines,
        do_async,
        apply=apply)

    for line in gen:
        click.echo(line, nl=False)
