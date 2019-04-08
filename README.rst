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





Given a server responding to ``http://localhost:8080/`` and a list of urls in ``urls.txt`` : ::

  http://localhost:8080/Requester_254
  http://localhost:8080/Requester_083
  http://localhost:8080/Requester_128
  http://localhost:8080/Requester_064
  http://localhost:8080/Requester_276


Automatically import required modules and use their functions: ::

   $ pype map 'x.strip() ! requests.get(x) ! x.text ' < urls.txt

   Hello, Requester_254. You are client number 7903 for this server.
   Hello, Requester_083. You are client number 7904 for this server.
   Hello, Requester_128. You are client number 7905 for this server.
   Hello, Requester_064. You are client number 7906 for this server.
   Hello, Requester_276. You are client number 7907 for this server.


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

   $ time python3.7 -m poetry run python -m pype map 'await asks.get ! x.text ! len' apply max <<EOF
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
   short_help = "Load jsonlines into python objects"

   [[alias.stage]]

   name= "map"
   options = []
   arguments = [ "json.loads ! attr.make_class('X', list(x.keys()))(**x)"]




Now we can use it like a regular command: ::

    $ pype jsonl  <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
    X(a=1, b=2)
    X(a=5, b=9)



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
