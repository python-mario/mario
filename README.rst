pype: command-line pipes in Python
####################################

Usage
=====




At the command prompt, use ``pype`` to act on each item in the file with python commands: ::

  $ printf 'abc' | pype str.upper

  ABC


Chain python functions together with ``!``: ::

  $ printf 'Hello'  | pype 'str.upper ! len'

  5

Use ``?`` as a placeholder for the input at each stage: ::

  $ printf 'Hello World'  | pype 'str.split ! ?[0].upper() + "!"'

  HELLO!

  $ printf 'Hello World'  | pype 'str.split ! ?[0].upper() + "!" ! ?.replace("H", "J")'

  JELLO!



Given a server responding to ``http://localhost:8080/`` and a list of urls in ``urls.txt`` : ::

  http://localhost:8080/Requester_254
  http://localhost:8080/Requester_083
  http://localhost:8080/Requester_128
  http://localhost:8080/Requester_064
  http://localhost:8080/Requester_276


Automatically import required modules and use their functions: ::

   $ pype 'str.strip ! requests.get ! ?.text ' < urls.txt

   Hello, Requester_254. You are client number 7903 for this server.
   Hello, Requester_083. You are client number 7904 for this server.
   Hello, Requester_128. You are client number 7905 for this server.
   Hello, Requester_064. You are client number 7906 for this server.
   Hello, Requester_276. You are client number 7907 for this server.


Use ``map`` to act on each input item (``map`` is the default command). Use ``apply`` to act on the sequence of items. Finding the largest number returned from the server: ::

    $ pype --newlines=no map 'str.strip ! requests.get ! ?.text ! ?.split()[6] ! int' apply 'max'  < urls.txt

    7933


Making sequential requests is slow. Use ``--async`` to make I/O really fast (see caveats below). ::

  $ time pype 'str.strip ! requests.get ! ?.text'  < urls.txt

  Hello, Requester_254. You are client number 8061 for this server.
  Hello, Requester_083. You are client number 8062 for this server.
  Hello, Requester_128. You are client number 8063 for this server.
  Hello, Requester_064. You are client number 8064 for this server.
  Hello, Requester_276. You are client number 8065 for this server.

  real	0m10.640s
  user	0m0.548s
  sys	0m0.022s


Making concurrent requests is much faster: ::

   $ time pype --async 'str.strip ! treq.get ! treq.text_content'  < urls.txt

   Hello, Requester_254. You are client number 8025 for this server.
   Hello, Requester_083. You are client number 8025 for this server.
   Hello, Requester_128. You are client number 8025 for this server.
   Hello, Requester_064. You are client number 8025 for this server.
   Hello, Requester_276. You are client number 8025 for this server.

   real	0m2.626s
   user	0m0.574s
   sys	0m0.044s



Installation
============

``pip install python-pype``


Caveats
=======


* ``pype`` assumes *trusted command arguments* and *untrusted input stream data*. It uses ``eval`` on your arguments, not on the input stream data. If you use ``exec``, ``eval``, ``subprocess``, or similar commands, you can execute arbitrary code from the input stream.

* ``--async`` currently works only with ``map``, not ``apply`` and works only for a single ``map`` pipe-string, e.g. ``map 'str.upper ! len ! ? & 1'``, not for chains, e.g. ``map str.upper map len map '? & 1'``.




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
