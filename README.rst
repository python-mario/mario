``````````````````````````````````````````````````````
Mario: Shell pipes in Python
``````````````````````````````````````````````````````

Your favorite plumbing snake 🐍🔧 with your favorite pipes, right in your shell 🐢.



.. image:: https://readthedocs.org/projects/python-mario/badge/?style=flat
   :target: https://readthedocs.org/projects/python-mario
   :alt: Documentation Status

.. image:: https://travis-ci.com/python-mario/mario.svg?branch=master
   :target: https://travis-ci.com/python-mario/mario#
   :alt: Build status

.. image:: https://img.shields.io/pypi/v/mario.svg
   :target: https://pypi.python.org/pypi/mario
   :alt: PyPI package

.. image:: https://img.shields.io/codecov/c/github/python-mario/mario.svg
   :target: https://codecov.io/gh/python-mario/mario
   :alt: Coverage



&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
Installation
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&


..
    installation-inclusion-start

Mario
***********************************************************


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

Use ``map`` to act on each item in the file with python commands:

.. code-block:: bash

  $ mario map str.upper <<<'abc'
  ABC


Chain python functions together with ``!``:

.. code-block:: bash

  $ mario map 'str.upper ! len' <<<hello
  5

or by adding another command

.. code-block:: bash

   $ mario map str.upper map len <<<hello
   5


Use ``x`` as a placeholder for the input at each stage:

.. code-block:: bash

  $ mario map ' x.split()[0] ! x.upper()' <<<'Hello world'
  HELLO

  $ mario map 'x.split()[0] ! x.upper() ! x.replace("H", "J")' <<<'Hello world'
  JELLO



Automatically import modules you need:

.. code-block:: bash

    $ mario map 'collections.Counter ! dict' <<<mississippi
    {'m': 1, 'i': 4, 's': 4, 'p': 2}


You don't need to explicitly call the function with ``some_function(x)``; just use the function's name, ``some_function``. For example, instead of

.. code-block:: bash

  $ mario map 'len(x)' <<<'a\nbb'
  5

try

.. code-block:: bash

  $ mario map len <<<'a\nbb'
  5




More commands
***********************************************************

Here are a few commands. See `Command reference <cli_reference.html>`__ for the complete set, and get even more from `mario-addons <https://mario-addons.readthedocs.org/>`__.


``eval``
----------------------------------------------------


Use ``eval`` to evaluate a Python expression.

.. code-block:: bash

  $ mario eval 'datetime.datetime.utcnow()'
  2019-01-01 01:23:45.562736



``map``
----------------------------------------------------

Use ``map`` to act on each input item.

.. code-block:: bash

   $ mario map 'x * 2' <<<'a\nbb\n'
   aa
   bbbb

``filter``
----------------------------------------------------


Use ``filter`` to evaluate a condition on each line of input and exclude false values.

.. code-block:: bash

   $  mario filter 'len(x) > 1' <<<'a\nbb\nccc\n'
   bb
   ccc


``apply``
----------------------------------------------------

Use ``apply`` to act on the sequence of items.

.. code-block:: bash

    $ mario apply 'len(x)' <<<$'a\nbb'
    2



``reduce``
----------------------------------------------------

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
----------------------------------------------------

Use ``chain`` to flatten an iterable of iterables of items into an iterable of items, like `itertools.chain.from_iterable <https://docs.python.org/3/library/itertools.html#itertools.chain.from_iterable>`_.

For example, after calculating a several rows of items,

.. code-block:: bash


    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]'   <<EOF
    ab
    ce
    EOF
    ['ab', 'ba', 'ab', 'b']
    ['ce', 'ec', 'ce', 'e']


use ``chain`` to put each item on its own row:

.. code-block:: bash

    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]' chain  <<EOF
    ab
    ce
    EOF
    ab
    ba
    ab
    b
    ce
    ec
    ce
    e

Then subsequent commands will act on these new rows. Here we get the length of each row.

.. code-block:: bash

    $ mario  map 'x*2 ! [x[i:i+2] for i in range(len(x))]' chain map len <<EOF
    ab
    ce
    EOF
    2
    2
    2
    1
    2
    2
    2
    1



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
