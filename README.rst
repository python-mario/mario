mario: command-line pipes in Python
####################################

Usage
=====

Basics
~~~~~~


At the command prompt, use ``mario`` to act on each item in the file with python commands: ::

  $ mario map x.upper() <<<'abc'
  ABC


Chain python functions together with ``!``: ::

  $ mario map 'x.upper() ! len(x)' <<<hello
  5

or by adding another command like  ``map <pipeline>`` ::

   $ mario map 'x.upper()' map 'len(x)' <<<hello
   5


Use ``x`` as a placeholder for the input at each stage: ::

  $ mario map ' x.split()[0] ! x.upper() + "!"' <<<'Hello world'
  HELLO!

  $ mario map 'x.split()[0] ! x.upper() + "!" ! x.replace("H", "J")' <<<'Hello world'
  JELLO!



Automatically import modules you need: ::

   $ mario stack 'itertools.repeat(x, 2) ! "".join' <<<hello,world!
   hello,world!
   hello,world!



Commands
~~~~~~~~

``map``
_______

Use ``map`` to act on each input item. ::

   $ mario map 'x * 2' <<<'a\nbb\n'
   aa
   bbbb

``filter``
__________


Use ``filter`` to evaluate a condition on each line of input and exclude false values. ::

   $  mario filter 'len(x) > 1' <<<'a\nbb\nccc\n'
   bb
   ccc


``apply``
_________

Use ``apply`` to act on the sequence of items. ::

    $   mario apply 'len(x)' <<<'a\nbb\n'
    2


``stack``
_________

Use ``stack`` to treat the input as a single string, including newlines. ::

    $  mario stack 'len(x)' <<<'a\nbb\n'
    5

Use ``eval`` to evaluate a python expression without any input. ::

   $ mario eval 1+1
   2

``reduce``
__________

Use ``reduce`` to evaluate a function of two arguments successively over a sequence, like `functools.reduce <https://docs.python.org/3/library/functools.html#functools.reduce>`_.

For example, to multiply all the values together, first convert each value to ``int`` with ``map``, then use ``reduce`` to successively multiply each item with the product. ::


   $ mario map int reduce operator.mul <<EOF
   1
   2
   3
   4
   EOF

   24




Autocall
~~~~~~~~

You don't need to explicitly call the function with ``f(x)``; just use ``f``. For example, instead of ::

  $ mario map 'len(x)' <<<'a\nbb'
  5

try ::

  $ mario map len <<<'a\nbb'
  5



Async
~~~~~

Making sequential requests is slow. These requests take 20 seconds to complete. ::

   $ time mario map 'requests.get ! x.text ! len' apply max <<EOF
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

Concurrent requests can go much faster. The same requests now take only 6 seconds. Use ``amap``, or ``afilter``, or ``reduce`` with ``await some_async_function`` to get concurrency out of the box. ::

   $ time mario amap 'await asks.get ! x.text ! len' apply max <<EOF
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

``amap`` and ``afilter`` values are handled in streaming fashion, while retaining the order of the input items in the output. The order of function calls is not constrained -- if you need the function to be **called** with items in a specific order, use the synchronous version.

Making concurrent requests, each response is printed one at a time, as soon as (1) it is ready and (2) all of the preceding requests have already been handled.

For example, the ``3 seconds`` item is ready before the preceding ``4 seconds`` item, but it is held until the ``4 seconds`` is ready because ``4 seconds`` was started first, so the ordering of the input items is maintained in the output.

::

    $ time mario --exec-before 'import datetime; now=datetime.datetime.utcnow; START_TIME=now(); print("Elapsed time | Response size")' map 'await asks.get !  f"{(now() - START_TIME).seconds} seconds    | {len(x.content)} bytes"'  <<EOF
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

Add code to automatically execute, into your config file.

For example: ::

  # ~/.config/mario/config.toml

  exec_before = """

  from itertools import *
  from collections import Counter

  """

Then you can directly use the imported objects without referencing the module. ::


    $ mario map 'Counter ! json.dumps' <<<'hello\nworld\n'
    {"h": 1, "e": 1, "l": 2, "o": 1}
    {"w": 1, "o": 1, "r": 1, "l": 1, "d": 1}


You can set any of the ``mario`` options in your config. For example, to set a different default value for the concurrency maximum ``mario --max-concurrent``, add ``max_concurrent`` to your config file (note the underscore): ::

  # ~/.config/mario/config.toml

  max_concurrent = 10

then just use ``mario`` as normal.



Aliases
~~~~~~~~~~~~~~~~~~

Define new commands in your config file which provide aliases to other commands. For example, this config adds a ``jsonl`` command for reading jsonlines streams into Python objects, by calling calling out to the ``map`` traversal. ::


   [[alias]]

   name = "jsonl"
   short_help = "Load jsonlines into python objects."

   [[alias.stage]]

   command = "map"
   options = []
   arguments = [ "json.loads ! types.SimpleNameSpace(**x)" ]


Now we can use it like a regular command: ::

    $ mario jsonl  <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
    X(a=1, b=2)
    X(a=5, b=9)


The new command ``jsonl`` can be used in pipelines as well. To get the maximum value in a sequence of jsonlines objects. ::

   $ mario jsonl map 'x.a' apply max <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
   5


Plugins
~~~~~~~

Add new commands like ``map`` and ``reduce`` by installing mario plugins. You can try them out without installing by adding them to any ``.py`` file in your ``~/.config/mario/modules/``.


Installation
============

Get it with pip: ::

   pip install python-mario


Caveats
=======


* ``mario`` assumes *trusted command arguments* and *untrusted input stream data*. It uses ``eval`` on your commands, not on the input stream data. If you use ``exec``, ``eval``, ``subprocess``, or similar commands, you can execute arbitrary code from the input stream, like in regular python.


Status
======

* Check the `issues page <https://www.github.com/python-mario/mario/issues>`_ for open tickets.
* This package is experimental and is subject to change without notice.


Related work
============

* https://github.com/Russell91/pythonpy
* http://gfxmonk.net/dist/doc/piep/
* https://spy.readthedocs.io/en/latest/intro.html
* https://github.com/ksamuel/Pyped
* https://github.com/ircflagship2/mario
