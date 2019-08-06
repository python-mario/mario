``````````````````````````````````````````````````````
Mario: Shell pipes in Python
``````````````````````````````````````````````````````



.. image:: https://img.shields.io/github/stars/python-mario/mario?style=social
   :target: https://github.com/python-mario/mario
   :alt: GitHub

.. image:: https://readthedocs.org/projects/python-mario/badge/?style=flat
   :target: https://readthedocs.org/projects/python-mario
   :alt: Documentation Status

.. image:: https://img.shields.io/travis/com/python-mario/mario/master
   :target: https://travis-ci.com/python-mario/mario#
   :alt: Build status

.. image:: https://img.shields.io/pypi/v/mario.svg
   :target: https://pypi.python.org/pypi/mario
   :alt: PyPI package

.. image:: https://img.shields.io/codecov/c/github/python-mario/mario.svg
   :target: https://codecov.io/gh/python-mario/mario
   :alt: Coverage

Have you ever wanted to use Python functions directly in your Unix shell? Mario can read and write csv, json, and yaml; traverse trees, and even do xpath queries. Plus, it supports async commands right out of the box. Build your own commands with a simple configuration file, and install plugins for even more!

Mario is the plumbing snake 🐍🔧 helping you build data pipelines in your shell 🐢.


.. image:: https://raw.githubusercontent.com/python-mario/mario/master/docs/time.png
   :alt: What time is it in Sydney?


&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Features
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&


- Execute Python code in your shell.
- Pass Python objects through multi-stage pipelines.
- Read and write csv, json, yaml, toml, xml.
- Run async functions natively.
- Define your own commands in a simple configuration file or by writing Python code.
- Install plugins to get more commands.
- Enjoy high test coverage, continuous integration, and nightly releases.


&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Installation
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&


..
    installation-inclusion-start

Mario
***********************************************************


Windows support is hopefully coming soon. Linux and MacOS are supported now.

Get Mario with pip:

.. code-block:: bash

   python3.7 -m pip install mario

If you're not inside a virtualenv, you might get a ``PermissionsError``. In that case, try using:

.. code-block:: bash

    python3.7 -m pip install --user mario

or for more isolation, use `pipx <https://github.com/pipxproject/pipx/>`_:

.. code-block:: bash

     pipx install --python python3.7 mario



Mario addons
***********************************************************

The `mario-addons <https://mario-addons.readthedocs.io/>`__ package provides a number of useful commands not found in the base collection.


Get Mario addons with pip:

.. code-block:: bash

   python3.7 -m pip install mario-addons

If you're not inside a virtualenv, you might get a ``PermissionsError``. In that case, try using:

.. code-block:: bash

    python3.7 -m pip install --user mario-addons

or for more isolation, use `pipx <https://github.com/pipxproject/pipx/>`_:

.. code-block:: bash

     pipx install --python python3.7 mario
     pipx inject mario mario-addons



..
    installation-inclusion-end




&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Quickstart
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

Basics
***********************************************************

Invoke with  ``mario`` at the command line.

.. code-block:: bash

    $ mario eval 1+1
    2


Given a csv like this:


.. code-block:: bash

    $ cat <<EOF > hackers.csv
    name,age
    Alice,21
    Bob,22
    Carol,23
    EOF

Use ``read-csv-dicts`` to read each row into a dict:

.. code-block:: bash

    $ mario read-csv-dicts < hackers.csv
    {'name': 'Alice', 'age': '21'}
    {'name': 'Bob', 'age': '22'}
    {'name': 'Carol', 'age': '23'}


Use ``map`` to act on each input item ``x`` :

.. code-block:: bash

    $ mario read-csv-dicts map 'x["name"]' < hackers.csv
    Alice
    Bob
    Carol

Chain Python functions together with ``!``:

.. code-block:: bash

    $ mario read-csv-dicts map 'x["name"] ! len' < hackers.csv
    5
    3
    5

or by adding another command

.. code-block:: bash

    $ mario read-csv-dicts map 'x["name"]' map len < hackers.csv
    5
    3
    5


Use ``x`` as a placeholder for the input at each stage:

.. code-block:: bash

    $ mario read-csv-dicts map 'x["age"] ! int ! x*2'  < hackers.csv
    42
    44
    46


Automatically import modules you need:

.. code-block:: bash

    $ mario map 'collections.Counter ! dict' <<<mississippi
    {'m': 1, 'i': 4, 's': 4, 'p': 2}


You don't need to explicitly call the function with ``some_function(x)``; just use the function's name, ``some_function``. For example, instead of

.. code-block:: bash

    $ mario map 'len(x)' <<EOF
    a
    bb
    EOF
    1
    2

try

.. code-block:: bash

    $ mario map len <<EOF
    a
    bb
    EOF
    1
    2




More commands
***********************************************************

Here are a few commands. See `Command reference <https://python-mario.readthedocs.io/en/latest/cli_reference.html>`_ for the complete set, and get even more from `mario-addons <https://mario-addons.readthedocs.org/>`__.


``eval``
----------------------------------------------------


Use ``eval`` to evaluate a Python expression.

.. code-block:: bash

    % mario eval 'datetime.datetime.utcnow()'
   2019-01-01 01:23:45.562736



``map``
----------------------------------------------------

Use ``map`` to act on each input item.

.. code-block:: bash

    $ mario map 'x * 2' <<EOF
    a
    bb
    EOF
    aa
    bbbb

``filter``
----------------------------------------------------


Use ``filter`` to evaluate a condition on each line of input and exclude false values.

.. code-block:: bash

    $ mario filter 'len(x) > 1' <<EOF
    a
    bb
    ccc
    EOF
    bb
    ccc


``apply``
----------------------------------------------------

Use ``apply`` to act on the sequence of items.

.. code-block:: bash

    $ mario apply 'len(x)' <<EOF
    a
    bb
    EOF
    2




``chain``
----------------------------------------------------

Use ``chain`` to flatten a list of lists into a single list, like `itertools.chain.from_iterable <https://docs.python.org/3/library/itertools.html#itertools.chain.from_iterable>`_.

For example, after generating a several rows of items,

.. code-block:: bash


    $ mario read-csv-tuples <<EOF
    a,b,c
    d,e,f
    g,h,i
    EOF
    ('a', 'b', 'c')
    ('d', 'e', 'f')
    ('g', 'h', 'i')



use ``chain`` to put each item on its own row:

.. code-block:: bash

    $ mario read-csv-tuples chain <<EOF
    a,b,c
    d,e,f
    g,h,i
    EOF
    a
    b
    c
    d
    e
    f
    g
    h
    i



``async-map``
----------------------------------------------------

..
    async-inclusion-start

Making sequential requests is slow. These requests take 16 seconds to complete.

.. code-block:: bash


       % time mario map 'await asks.get ! x.json()["url"]'  <<EOF
       http://httpbin.org/delay/5
       http://httpbin.org/delay/1
       http://httpbin.org/delay/2
       http://httpbin.org/delay/3
       http://httpbin.org/delay/4
       EOF
       https://httpbin.org/delay/5
       https://httpbin.org/delay/1
       https://httpbin.org/delay/2
       https://httpbin.org/delay/3
       https://httpbin.org/delay/4
       0.51s user
       0.02s system
       16.460 total


Concurrent requests can go much faster. The same requests now take only 6 seconds. Use ``async-map``, or ``async-filter``, or ``reduce`` with ``await some_async_function`` to get concurrency out of the box.


.. code-block:: bash


       % time mario async-map 'await asks.get ! x.json()["url"]'  <<EOF
       http://httpbin.org/delay/5
       http://httpbin.org/delay/1
       http://httpbin.org/delay/2
       http://httpbin.org/delay/3
       http://httpbin.org/delay/4
       EOF
       https://httpbin.org/delay/5
       https://httpbin.org/delay/1
       https://httpbin.org/delay/2
       https://httpbin.org/delay/3
       https://httpbin.org/delay/4
       0.49s user
       0.03s system
       5.720 total

..
    async-inclusion-end

.. _config-intro:

&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Configuration
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&


Define new commands and set default options. See `Configuration reference <config_reference.html>`_ for details.


&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Plugins
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

Add new commands like ``map`` and ``reduce`` by installing Mario plugins. You can try them out without installing by adding them to any ``.py`` file in your ``~/.config/mario/modules/``.

Share popular commands by installing the `mario-addons <https://mario-addons.readthedocs.io/en/latest/readme.html>`_ package.



&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Q & A
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&


..
    Q&A-inclusion-start



What's the status of this package?
***********************************************************

* This package is experimental and is subject to change without notice.
* Check the `issues page <https://www.github.com/python-mario/mario/issues>`_ for open tickets.


Why another package?
***********************************************************

A number of cool projects have pioneered in the Python-in-shell space. I wrote Mario because I didn't know these existed at the time, but now Mario has a bunch of features the others don't (user configuration, multi-stage pipelines, async, plugins, etc).

* https://github.com/Russell91/pythonpy
* http://gfxmonk.net/dist/doc/piep/
* https://spy.readthedocs.io/en/latest/intro.html
* https://github.com/ksamuel/Pyped
* https://github.com/ircflagship2/pype


..
    Q&A-inclusion-end
