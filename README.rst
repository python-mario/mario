pype: command-line pipes in Python
####################################

Usage
=====

Basics
~~~~~~


At the command prompt, use ``pype`` to act on each item in the file with python commands: ::

  $ pype map x.upper() <<<'abc'
  ABC


Chain python functions together with ``!``: ::

  $ pype map 'x.upper() ! len(x)' <<<hello
  5

Use ``x`` as a placeholder for the input at each stage: ::

  $ pype map ' x.split() ! x[0].upper() + "!"' <<<'Hello world'
  HELLO!

  $ pype map 'x.split() ! x[0].upper() + "!" ! x.replace("H", "J")' <<<'Hello world'
  JELLO!



Automatically import modules you need: ::

   $ pype stack 'itertools.repeat(x, 2) ! "".join' <<<hello,world!
   hello,world!
   hello,world!



Commands
~~~~~~~~

``map``
_______

Use ``map`` to act on each input item. ::

   $ pype map 'x * 2' <<<'a\nbb\n'
   aa
   bbbb

``filter``
__________


Use ``filter`` to evaluate a condition on each line of input and exclude false values. ::

   $  pype filter 'len(x) > 1' <<<'a\nbb\nccc\n'
   bb
   ccc


``apply``
_________

Use ``apply`` to act on the sequence of items. ::

    $   pype apply 'len(x)' <<<'a\nbb\n'
    2


``stack``
_________

Use ``stack`` to treat the input as a single string, including newlines. ::

    $  pype stack 'len(x)' <<<'a\nbb\n'
    5

Use ``eval`` to evaluate a python expression without any input. ::

   $ pype eval 1+1
   2

``reduce``
__________

Use ``reduce`` to evaluate a function of two arguments successively over a sequence, like `functools.reduce <https://docs.python.org/3/library/functools.html#functools.reduce>`_ ::


   $ pype map int reduce operator.mul <<EOF
   1
   2
   3
   4
   EOF

   24


Autocall
~~~~~~~~

You don't need to explicitly call the function with ``f(x)``; just use ``f``. For example, instead of ::

  $ pype map 'len(x)' <<<'a\nbb'
  5

try ::

  $ pype map len <<<'a\nbb'
  5



Async
~~~~~

Making sequential requests is slow. These requests take 18 seconds to complete. ::

   $ time pype map 'requests.get ! x.text ! len' apply max <<EOF
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

Concurrent requests can go much faster. The same requests now take only 5 seconds. Just use ``await async_function`` to get concurrency out of the box. ::

   $ time pype map 'await asks.get ! x.text ! len' apply max <<EOF
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


Streaming
~~~~~~~~~

``map`` and ``filter`` values are handled in streaming fashion, while retaining order.

Making concurrent requests, each response is printed one at a time, as soon as (1) it is ready and (2) all of the preceding requests have already been handled.

For example, the ``3 seconds`` item is ready before the preceding ``4 seconds`` item, but it is held until the ``4 seconds`` is ready because ``4 seconds`` was started first, so the ordering is maintained.

::

    $ time pype --exec-before 'import datetime; now=datetime.datetime.utcnow; START_TIME=now(); print("Elapsed time | Response size")' map 'await asks.get !  f"{(now() - START_TIME).seconds} seconds    | {len(x.content)} bytes"'  <<EOF
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

  # ~/.config/pype/config.toml

  exec_before = """

  from itertools import *
  from collections import Counter

  """

Then you can directly use the imported objects without referencing the module. ::


    $ printf 'hello\nworld\n' | pype --autocall map 'Counter ! json.dumps'

    {"h": 1, "e": 1, "l": 2, "o": 1}
    {"w": 1, "o": 1, "r": 1, "l": 1, "d": 1}


You can set any of the ``pype`` options in your config. For example, to make ``--no-autocall`` the default, add ::

  # ~/.config/pype/config.toml

  autocall = false

then just use ``pype`` as normal ::

   $ printf 'a\nbb\nccc\n' | pype map 'len'
   <built-in function len>
   <built-in function len>
   <built-in function len>


Aliases
~~~~~~~~~~~~~~~~~~

Define new commands in your config file which provide aliases to other commands. For example, this config adds a ``jsonl`` command for reading jsonlines streams into Python objects, by calling calling out to the ``map`` traversal. ::


   [[alias]]

   name = "jsonl"
   short_help = "Load jsonlines into python objects."

   [[alias.stage]]

   name= "map"
   options = []
   arguments = [ "json.loads ! attr.make_class('X', list(x.keys()))(**x)"]


Now we can use it like a regular command: ::

    $ pype jsonl  <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
    X(a=1, b=2)
    X(a=5, b=9)


The new command ``jsonl`` can be used in pipelines as well. To get the maximum value in a sequence of jsonlines objects. ::

   $ pype jsonl map 'x.a' apply max <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
   5


Installation
============

Get it with pip: ::

   pip install python-pype


Caveats
=======


* ``pype`` assumes *trusted command arguments* and *untrusted input stream data*. It uses ``eval`` on your commands, not on the input stream data. If you use ``exec``, ``eval``, ``subprocess``, or similar commands, you can execute arbitrary code from the input stream, like in regular python.


Status
======

* Check the `issues page <https://www.github.com/python-pype/pype/issues>`_ for open tickets.
* This package is experimental pre-alpha and is subject to change.


Related work
============

* https://github.com/Russell91/pythonpy
* http://gfxmonk.net/dist/doc/piep/
* https://spy.readthedocs.io/en/latest/intro.html
* https://github.com/ksamuel/Pyped
* https://github.com/ircflagship2/pype
