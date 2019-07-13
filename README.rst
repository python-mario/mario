
mario: command-line pipes in Python
===================================

Your favorite plumbing snake 🐍🔧 with your favorite pipes, right in your shell 🐢.


.. image:: https://travis-ci.com/python-mario/mario.svg?branch=master
           :target: https://travis-ci.com/python-mario/mario#

.. image:: https://img.shields.io/pypi/v/mario.svg
   :target: https://pypi.python.org/pypi/mario

.. image:: https://img.shields.io/codecov/c/github/python-mario/mario.svg
   :target: https://codecov.io/gh/python-mario/mario


Installation
============

Get it with pip:

.. code-block:: bash

   python3.7 -m pip install mario

If you're not inside a virtualenv, you might get a ``PermissionsError``. In that case, try using:

.. code-block:: bash

    python3.7 -m pip install --user mario

or for more flexibility and safety, use `pipx <https://github.com/pipxproject/pipx/>`_:

.. code-block:: bash

     pipx install --python python3.7 mario

Usage
=====

Basics
~~~~~~

Invoke with  ``mario`` at the command line.

.. code-block:: bash

  $ mario eval 1+1
  2

Use ``map`` to act on each item in the file with python commands:

.. code-block:: bash

  $ mario map 'x.upper()' <<<'abc'
  ABC


Chain python functions together with ``!``:

.. code-block:: bash

  $ mario map 'x.upper() ! len(x)' <<<hello
  5

or by adding another command

.. code-block:: bash

   $ mario map 'x.upper()' map 'len(x)' <<<hello
   5


Use ``x`` as a placeholder for the input at each stage:

.. code-block:: bash

  $ mario map ' x.split()[0] ! x.upper() + "!"' <<<'Hello world'
  HELLO!

  $ mario map 'x.split()[0] ! x.upper() + "!" ! x.replace("H", "J")' <<<'Hello world'
  JELLO!



Automatically import modules you need:

.. code-block:: bash

   $ mario stack 'itertools.repeat(x, 2) ! "".join' <<<hello,world!
   hello,world!
   hello,world!


Autocall
~~~~~~~~

You don't need to explicitly call the function with ``some_function(x)``; just use the function's name ``some_function``. For example, instead of

.. code-block:: bash

  $ mario map 'len(x)' <<<'a\nbb'
  5

try

.. code-block:: bash

  $ mario map len <<<'a\nbb'
  5




Commands
~~~~~~~~


``eval``
________


Use ``eval`` to evaluate a Python expression.

.. code-block:: bash

  $ mario eval 'datetime.datetime.utcnow()'
  2019-01-01 01:23:45.562736



``map``
_______

Use ``map`` to act on each input item.

.. code-block:: bash

   $ mario map 'x * 2' <<<'a\nbb\n'
   aa
   bbbb

``filter``
__________


Use ``filter`` to evaluate a condition on each line of input and exclude false values.

.. code-block:: bash

   $  mario filter 'len(x) > 1' <<<'a\nbb\nccc\n'
   bb
   ccc


``apply``
_________

Use ``apply`` to act on the sequence of items.

.. code-block:: bash

    $ mario apply 'len(x)' <<<$'a\nbb'
    2


``stack``
_________

Use ``stack`` to treat the input as a single string, including newlines.

.. code-block:: bash

    $  mario stack 'len(x)' <<<$'a\nbb'
    5


``reduce``
__________

Use ``reduce`` to evaluate a function of two arguments successively over a sequence, like `functools.reduce <https://docs.python.org/3/library/functools.html#functools.reduce>`_.

For example, to multiply all the values together, first convert each value to ``int`` with ``map``, then use ``reduce`` to successively multiply each item with the product.

.. code-block:: bash


   $ mario map int reduce operator.mul <<EOF
   1
   2
   3
   4
   EOF

   24

``chain``
_________

Use ``chain`` to flatten an iterable of iterables of items into an iterable of items, like `itertools.chain.from_iterable <https://docs.python.org/3/library/itertools.html#itertools.chain.from_iterable>`_.

For example, after calculating a several rows of items,

.. code-block:: bash


    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]'   <<<$'ab\nce'
    ['ab', 'ba', 'ab', 'b']
    ['ce', 'ec', 'ce', 'e']


use ``chain`` to put each item on its own row:

.. code-block:: bash

    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]' chain  <<<$'ab\nce'
    ab
    ba
    ab
    b
    ce
    ec
    ce
    e

Then subsequent commands will act on these new rows, as normal. Here we get the length of each row.

.. code-block:: bash

    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]' chain map len <<<$'ab\nce'
    2
    2
    2
    1
    2
    2
    2
    1



Async
~~~~~

Making sequential requests is slow. These requests take 20 seconds to complete.

.. code-block:: bash

   % time mario map 'requests.get ! x.text ! len' apply max <<EOF
   http://httpbin.org/delay/5
   http://httpbin.org/delay/1
   http://httpbin.org/delay/4
   http://httpbin.org/delay/3
   http://httpbin.org/delay/4
   EOF

   302

   0.61s user
   0.06s system
   19.612 total

Concurrent requests can go much faster. The same requests now take only 6 seconds. Use ``async-map``, or ``async-filter``, or ``reduce`` with ``await some_async_function`` to get concurrency out of the box.

.. code-block:: bash

   % time mario async-map 'await asks.get ! x.text ! len' apply max <<EOF
   http://httpbin.org/delay/5
   http://httpbin.org/delay/1
   http://httpbin.org/delay/4
   http://httpbin.org/delay/3
   http://httpbin.org/delay/4
   EOF

   297

   0.57s user
   0.08s system
   5.897 total


Async streaming
~~~~~~~~~~~~~~~

``async-map`` and ``async-filter`` values are handled in streaming fashion, while retaining the order of the input items in the output. The order of function calls is not constrained -- if you need the function to be **called** with items in a specific order, use the synchronous version.

Making concurrent requests, each response is printed one at a time, as soon as (1) it is ready and (2) all of the preceding requests have already been handled.

For example, the ``3 seconds`` item is ready before the preceding ``4 seconds`` item, but it is held until the ``4 seconds`` is ready because ``4 seconds`` was started first, so the ordering of the input items is maintained in the output.



.. code-block:: bash

    % time mario --exec-before 'import datetime; now=datetime.datetime.utcnow; START_TIME=now(); print("Elapsed time | Response size")' map 'await asks.get !  f"{(now() - START_TIME).seconds} seconds    | {len(x.content)} bytes"'  <<EOF
    http://httpbin.org/delay/1
    http://httpbin.org/delay/2
    http://httpbin.org/delay/4
    http://httpbin.org/delay/3
    EOF
    Elapsed time | Response size
    1 seconds    | 297 bytes
    2 seconds    | 297 bytes
    4 seconds    | 297 bytes
    3 seconds    | 297 bytes



Configuration
~~~~~~~~~~~~~

The config file location follows the `freedesktop.org standard <https://www.freedesktop.org/wiki/Software/xdg-user-dirs/>`_. Check the location on your system by running ``mario --help``:


.. code-block:: bash

    % mario --help
    Usage: mario [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

      Mario: Python pipelines for your shell.

      GitHub: https://github.com/python-mario/mario

      Configuration:
        Declarative config: /home/user/.config/mario/config.toml
        Python modules: /home/user/.config/mario/modules/*.py




For example on Ubuntu we use ``~/.config/mario/config.toml`` for declarative configuration. Add code and settings into your config.



.. code-block:: toml

  # ~/.config/mario/config.toml

  base_exec_before = """

  from itertools import *
  from collections import Counter

  """

Then you can directly use the imported objects without referencing the module.

.. code-block:: bash


    % mario map 'Counter ! json.dumps' <<<$'hello\nworld'
    {"h": 1, "e": 1, "l": 2, "o": 1}
    {"w": 1, "o": 1, "r": 1, "l": 1, "d": 1}


You can set any of the ``mario`` options in your config. For example, to set a different default value for the concurrency maximum ``mario --max-concurrent``, add ``max_concurrent`` to your config file (note the underscore):

.. code-block:: toml

    # ~/.config/mario/config.toml

    max_concurrent = 10

then just use ``mario`` as normal.



Aliases
~~~~~~~~~~~~~~~~~~

Define new commands in your config file which provide aliases to other commands. For example, this config adds a ``jsonl`` command for reading jsonlines streams into Python objects, by calling calling out to the ``map`` traversal.

.. code-block:: toml

   [[alias]]

   name = "jsonl"
   help = "Load jsonlines into python objects."

   [[alias.stage]]

   command = "map"
   options = {code="json.loads"}


Now we can use it like a regular command:

.. code-block:: bash

    % mario jsonl  <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
    {'a': 1, 'b': 2}
    {'a': 5, 'b': 9}


The new command ``jsonl`` can be used in pipelines as well. To get the maximum value in a sequence of jsonlines objects:

.. code-block:: bash

   $ mario jsonl map 'x.a' apply max <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
   5

More alias examples
____________________


Convert yaml to json
++++++++++++++++++++++++

Convenient for removing trailing commas.

.. code-block:: bash

    % mario yml2json <<<'{"x": 1,}'
    {"x": 1}

.. code-block:: toml

    [[alias]]

        name = "yml2json"
        help = "Convert yaml to json"

        [[alias.stage]]

        command = "stack"
        options = {code="yaml.safe_load ! json.dumps"}

Search for xpath elements with xpath
+++++++++++++++++++++++++++++++++++++++++

Pull text out of xml documents.

.. code-block:: bash


    % mario xpath '//'  map 'x.text' <<EOF
          <slide type="all">
            <title>Overview</title>
              <item>Anything <em>can be</em> in here</item>
              <item>Or <em>also</em> in here</item>
          </slide>
    EOF

    Overview
    Anything
    can be
    Or
    also




.. code-block:: toml

    [[alias]]
        name="xpath"
        help = "Find xml elements matching xpath query."
        arguments = [{name="query", type="str"}]
        inject_values=["query"]

        [[alias.stage]]
        command = "stack"
        options= {code="x.encode() ! io.BytesIO ! lxml.etree.parse ! x.findall(query) ! list" }

        [[alias.stage]]
        command="chain"


Generate json objects
++++++++++++++++++++++

.. code-block:: bash

    % mario jo 'name=Alice age=21 hobbies=["running"]'
    {"name": "Alice", "age": 21, "hobbies": ["running"]}


.. code-block:: toml

    [[alias]]


        name="jo"
        help="Make json objects"
        arguments=[{name="pairs", type="str"}]
        inject_values=["pairs"]

        [[alias.stage]]
        command = "eval"
        options = {code="pairs"}

        [[alias.stage]]
        command = "map"
        options = {code="shlex.split(x, posix=False)"}

        [[alias.stage]]
        command = "chain"

        [[alias.stage]]
        command = "map"
        options = {code="x.partition('=') ! [x[0], ast.literal_eval(re.sub(r'^(?P<value>[A-Za-z]+)$', r'\"\\g<value>\"', x[2]))]"}

        [[alias.stage]]
        command = "apply"
        options = {"code"="dict"}

        [[alias.stage]]
        command = "map"
        options = {code="json.dumps"}



Read csv file
+++++++++++++

Read a csv file into Python dicts. Given a csv like this:


.. code-block:: bash

    % cat names.csv
    name,age
    Alice,21
    Bob,25

try:

.. code-block:: bash

    % mario csv < names.csv
    {'name': 'Alice', 'age': '21'}
    {'name': 'Bob', 'age': '25'}


.. code-block:: toml

    base_exec_before = '''
    import csv
    import typing as t


    def read_csv(
        file, header: bool, **kwargs
    ) -> t.Iterable[t.Dict[t.Union[str, int], str]]:
        "Read csv rows into an iterable of dicts."

        rows = list(file)

        first_row = next(csv.reader(rows))
        if header:
            fieldnames = first_row
            reader = csv.DictReader(rows, fieldnames=fieldnames, **kwargs)
            return list(reader)[1:]

        fieldnames = range(len(first_row))
        return csv.DictReader(rows, fieldnames=fieldnames, **kwargs)

    '''




    [[alias]]
        name = "csv"
        help = "Load csv rows into python dicts. With --no-header, keys will be numbered from 0."
        inject_values=["delimiter", "header"]

        [[alias.options]]
        name = "--delimiter"
        default = ","
        help = "field delimiter character"

        [[alias.options]]
        name = "--header/--no-header"
        default=true
        help = "Treat the first row as a header?"

        [[alias.stage]]
        command = "apply"
        options = {code="read_csv(x, header=header)"}

        [[alias.stage]]
        command = "chain"

        [[alias.stage]]
        command = "map"
        options = {code="dict(x)"}



Plugins
~~~~~~~

Add new commands like ``map`` and ``reduce`` by installing mario plugins. You can try them out without installing by adding them to any ``.py`` file in your ``~/.config/mario/modules/``.



Caveats
=======


* ``mario`` assumes *trusted command arguments* and *untrusted input stream data*. It uses ``eval`` on your commands, not on the input stream data. If you use ``exec``, ``eval``, ``subprocess``, or similar commands, you can execute arbitrary code from the input stream, like in regular python.


Status
======

* Check the `issues page <https://www.github.com/python-mario/mario/issues>`_ for open tickets.
* This package is experimental and is subject to change without notice.


Related work
============

A number of cool projects have pioneered in the Python-in-shell space. I didn't know about these when I started writing Mario.  Mario has features missing from the others (user configuration, multi-stage pipelines, async, plugins, etc).

* https://github.com/Russell91/pythonpy
* http://gfxmonk.net/dist/doc/piep/
* https://spy.readthedocs.io/en/latest/intro.html
* https://github.com/ksamuel/Pyped
* https://github.com/ircflagship2/pype
