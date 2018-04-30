pype: command-line pipes with Python
####################################

Usage
=====




At the command prompt, use ``pype`` to act on each item in the file with python commands: ::

  $ printf 'abc' | pype str.upper

  ABC


Chain python functions together with ``||``: ::

  $ printf 'Hello'  | pype 'str.upper || len'

  5

Use ``?`` as a placeholder for the input at each stage: ::

  $ printf 'Hello World'  | pype 'str.split || ?[0].upper() + "!"'

  HELLO!

  $ printf 'Hello World'  | pype 'str.split || ?[0].upper() + "!" || ?.replace("H", "J")'

  JELLO!



Given a server responding to ``http://localhost:8080/`` and a list of urls in ``urls.txt`` : ::

  http://localhost:8080/Requester_254
  http://localhost:8080/Requester_083
  http://localhost:8080/Requester_128
  http://localhost:8080/Requester_064
  http://localhost:8080/Requester_276


Automatically import required modules and use their functions: ::

   $ pype 'str.strip || requests.get || ?.text ' < urls.txt

   Hello, Requester_254. You are client number 7903 for this server.
   Hello, Requester_083. You are client number 7904 for this server.
   Hello, Requester_128. You are client number 7905 for this server.
   Hello, Requester_064. You are client number 7906 for this server.
   Hello, Requester_276. You are client number 7907 for this server.


Use ``map`` to act on each input item (``map`` is the default command). Use ``apply`` to act on the sequence of items. Finding the largest number returned from the server: ::

    $ pype --newlines=no map 'str.strip || requests.get || ?.text || ?.split()[6] || int' apply 'max'  < urls.txt

    7933


Making sequential requests is slow. Use ``--async`` to make I/O really fast (see caveats below). ::

   $ time pype 'str.strip || requests.get || ?.text'  < urls.txt

   7938
   7939
   7940
   7941
   7942

   real	0m10.439s
   user	0m0.359s
   sys	0m0.025s


Making concurrent requests is much faster: ::

   $ time pype --async 'str.strip || treq.get || treq.text_content'  < urls.txt

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

TBD





Caveats
=======
* Security
  * If you use ``exec``, ``eval`` or ``subprocess`` commands, you can execute arbitrary code from the input.
  * There may be ways to make this package dangerous that I don't know about. Use it at your own risk.
* ```--async``
  * ``--async`` isn't throttled, so **please** use it only for small batches of requests (otherwise you may interfere with your target servers).
  * ``--async`` currently works only with ``pype map``, not ``pype apply`` and works only for a single ``map`` command, e.g. ``pype map 'str.upper || len || ? & 1``, not for chains, e.g. ``pype map str.upper map len map '? & 1'``.
  * ``--async`` works only with async APIs like ``treq`` instead of synchronous APIs like ``requests``.


Status
======

* This package is experimental pre-alpha and is subject to change.
