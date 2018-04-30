pype: command-line pipes with Python
####################################

USAGE
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


Use ``apply`` to act on the iterable. Here we get the largest number we receive from the server: ::

  $ pype --newlines=no map 'str.strip || requests.get || ?.text || ?.split()[6] || int' apply 'max'  < urls.txt
  7933


Installation
============

TBD
