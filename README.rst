pype: command-line pipes in Python
####################################

Usage
=====

Basics
~~~~~~


At the command prompt, use ``pype`` to act on each item in the file with python commands: ::

  $ printf 'abc' | pype map x.upper()

  ABC


Chain python functions together with ``!``: ::

  $ printf 'Hello'  | pype map 'x.upper() ! len(x)'

  5

Use ``x`` as a placeholder for the input at each stage: ::

  $ printf 'Hello World'  | pype map ' x.split() ! x[0].upper() + "!"'

  HELLO!

  $ printf 'Hello World'  | pype map 'x.split() ! x[0].upper() + "!" ! x.replace("H", "J")'

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


   $  printf 'a\nbb\n' | pype map 'x * 2'
   aa
   bbbb

``filter``
__________


Use ``filter`` to evaluate a condition on each line of input and exclude false values. ::

   $ printf 'a\nbb\nccc\n' | pype filter 'len(x) > 1'
   bb
   ccc


``apply``
_________

Use ``apply`` to act on the sequence of items. ::

    $ printf 'a\nbb\n' | pype apply 'len(x)'
    2


``stack``
_________

Use ``stack`` to treat the input as a single string, including newlines. ::

    $ printf 'a\nbb\n' | pype stack 'len(x)'
    5

Use ``eval`` to evaluate a python expression without any input. ::

   $ pype eval 1+1
   2

Options
~~~~~~~

``--autocall``
______________

If you're tired of writing all those ``f(x)``, use ``--autocall``, and just write ``f`` without the ``(x)``. ::

    $ printf 'hello\neverybody\n' | pype --autocall map 'len'
    5
    9


Async
~~~~~

Making sequential requests is slow. These requests take 10 seconds to complete. ::

  $ time pype map 'str.strip ! requests.get ! x.text'  < urls.txt

  Hello, Requester_254. You are client number 8061 for this server.
  Hello, Requester_083. You are client number 8062 for this server.
  Hello, Requester_128. You are client number 8063 for this server.
  Hello, Requester_064. You are client number 8064 for this server.
  Hello, Requester_276. You are client number 8065 for this server.

  real	0m10.640s
  user	0m0.548s
  sys	0m0.022s


Making concurrent requests is much faster: ::

   $ time pype map 'x.strip() ! await asks.get(x) ! x.text'  < urls.txt

   Hello, Requester_254. You are client number 8025 for this server.
   Hello, Requester_083. You are client number 8025 for this server.
   Hello, Requester_128. You are client number 8025 for this server.
   Hello, Requester_064. You are client number 8025 for this server.
   Hello, Requester_276. You are client number 8025 for this server.

   real	0m2.626s
   user	0m0.574s
   sys	0m0.044s


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
