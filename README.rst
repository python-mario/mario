pype: command-line pipes with Python
####################################

Usage
=====

Suppose we have a list of urls in ``urls.txt``: ::

  http://localhost:8080/Requester_254
  http://localhost:8080/Requester_083
  http://localhost:8080/Requester_128
  http://localhost:8080/Requester_064
  http://localhost:8080/Requester_276




At the command prompt, use ``map`` to act on each item in the file: ::

  $ pype map str.upper < urls.txt

   HTTP://LOCALHOST:8080/REQUESTER_254
   HTTP://LOCALHOST:8080/REQUESTER_083
   HTTP://LOCALHOST:8080/REQUESTER_128
   HTTP://LOCALHOST:8080/REQUESTER_064
   HTTP://LOCALHOST:8080/REQUESTER_276


   $ pype map '?.rsplit("/", 1) || "{}/{}".format(?[0], ?[1].upper())' < urls.txt

   http://localhost:8080/REQUESTER_254
   http://localhost:8080/REQUESTER_083
   http://localhost:8080/REQUESTER_128
   http://localhost:8080/REQUESTER_064
   http://localhost:8080/REQUESTER_276


   $ pype map 'str.strip || requests.get || ?.text ' < urls.txt # While running a local server

   Hello, Requester_254. You are client number 7903 for this server.
   Hello, Requester_083. You are client number 7904 for this server.
   Hello, Requester_128. You are client number 7905 for this server.
   Hello, Requester_064. You are client number 7906 for this server.
   Hello, Requester_276. You are client number 7907 for this server.

Use ``apply`` to act on the iterable. Finding the largest number returned from the server: ::

    $ pype --newlines=no map 'str.strip || requests.get || ?.text || ?.split()[6] || int' apply 'max'  < urls.txt

    7933


Use ``--async`` to make I/O really fast (see caveats below). Making sequential requests is slow: ::

   $ time pype map 'str.strip || requests.get || ?.text || ?.split()[6] || int'  < urls.txt

   7938
   7939
   7940
   7941
   7942

   real	0m10.439s
   user	0m0.359s
   sys	0m0.025s

Making concurrent requests is much faster: ::

   time pype --async map 'str.strip || treq.get || treq.text_content || ?.split()[6] || int'  < urls.txt

   7943
   7943
   7943
   7943
   7943

   real	0m2.435s
   user	0m0.385s
   sys	0m0.042s


* ``--async`` isn't throttled, so **please** use it only for small batches of requests (otherwise you may interfere with your target servers).
* ``--async`` currently works only with ``pype map``, not ``pype apply``.
* ``--async`` works only with async APIs like ``treq`` instead of synchronous APIs like ``requests``.


Installation
============

TBD


Status
======

* This package is experimental pre-alpha and changes often
