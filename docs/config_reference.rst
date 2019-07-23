
.. _config-reference:

=============================
Configuration
=============================

The configuration file is in `toml format <https://github.com/toml-lang/toml>`__. The file location follows the `freedesktop.org standard <https://www.freedesktop.org/wiki/Software/xdg-user-dirs/>`_. Check the location on your system by running ``mario --help``:


.. code-block:: bash

    % mario --help
    Usage: mario [OPTIONS] COMMAND1 [ARGS]... [COMMAND2 [ARGS]...]...

      Mario: Python pipelines for your shell.

      GitHub: https://github.com/python-mario/mario

      Configuration:
        Declarative config: /home/user/.config/mario/config.toml
        Python modules: /home/user/.config/mario/m/


Config modules
===============

Mario will make the ``m`` package available at startup. Define any functions you want for your commands in a file in the ``m/`` directory. For example, if you define a file called ``m/code.py`` in your config directory,


.. code-block:: python

    # m/code.py


    def increment(number):
        return number + 1

you can use ``m.code.increment`` in your commands, like this:

.. code-block:: bash


    % mario map 'int ! m.code.increment' <<EOF
    1
    2
    3
    EOF
    2
    3
    4


Any code that needs to run at startup, such as defining a new command, can be placed in ``m/__init__.py`` (or in the declarative config; see :ref:`Declarative configuration <declarative-config>`).

You also can add functions directly to the ``m`` namespace by placing them in ``m/__init__.py``. For example, defining ``increment`` in ``m/__init__.py``


.. code-block:: python

   # m/__init__.py


   def increment(number):
       return number + 1

allows invoking ``m.increment``, like this:

.. code-block:: bash

    % mario map 'int ! m.increment' <<EOF
    1
    2
    3
    EOF
    2
    3
    4

But note that Mario executes ``m/__init__.py`` at startup, so code placed in that file may affect startup time.


.. _declarative-config:

Declarative config
====================

The declarative configuration is in ``mario/mario.toml``. For example, on Ubuntu we use ``~/.config/mario/config.toml``.

In the declarative configuration you can:

* set default values for the ``mario`` command-line options, and
* define your own mario commands, like ``map``, ``filter``, or ``read-csv``.  See :ref:`Command configuration schema<command-config-schema>` for the command format specification.



You can set any of the ``mario`` command-line options in your config. For example, to set a different default value for the concurrency maximum ``mario --max-concurrent``, add ``max_concurrent`` to your config file. Note the configuration file uses underscores as word separators, not hyphens.

.. code-block:: toml

    # ~/.config/mario/config.toml

    max_concurrent = 10

then just use ``mario`` as normal.




The ``base_exec_before`` option allows you to define any Python code you want to execute before your commands run. Your commands can reference names defined in the ``base_exec_before``. This option can be supplemented by using the ``--exec-before`` option on the command line to run additional code before your commands.


.. code-block:: toml

  # ~/.config/mario/config.toml

  base_exec_before = """

  from itertools import *
  from collections import Counter

  """

Then you can directly use the imported objects without referencing the module.

.. code-block:: bash


    % mario map 'Counter ! json.dumps' <<<$'hello\nworld'
    {"h": 1, "e": 1, "l": 2, "o": 1}
    {"w": 1, "o": 1, "r": 1, "l": 1, "d": 1}



Custom commands
--------------------

Define new commands in your config file which provide commands to other commands. For example, this config adds a ``jsonl`` command for reading jsonlines streams into Python objects, by calling calling out to the ``map`` traversal.

Load jsonlines
++++++++++++++++

.. code-block:: toml

   [[command]]

   name = "jsonl"
   help = "Load jsonlines into python objects."

   [[command.stages]]

   command = "map"
   params = {code="json.loads"}


Now we can use it like a regular command:

.. code-block:: bash

    % mario jsonl  <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
    {'a': 1, 'b': 2}
    {'a': 5, 'b': 9}


The new command ``jsonl`` can be used in pipelines as well. To get the maximum value in a sequence of jsonlines objects:

.. code-block:: bash

   $ mario jsonl map 'x["a"]' apply max <<< $'{"a":1, "b":2}\n{"a": 5, "b":9}'
   5



Convert yaml to json
++++++++++++++++++++++++

Convenient for removing trailing commas.

.. code-block:: bash

    % mario yml2json <<<'{"x": 1,}'
    {"x": 1}

.. code-block:: toml

    [[command]]
    name = "yml2json"
    help = "Convert yaml to json"

    [[command.stages]]
    command = "read-text"

    [[command.stages]]
    command = "map"
    params = {code="yaml.safe_load ! json.dumps"}

Search for xml elements with xpath
+++++++++++++++++++++++++++++++++++++++++

Pull text out of xml documents.

.. code-block:: bash


    % mario xpath '//'  map 'x.text' <<EOF
          <slide type="all">
            <title>Overview</title>
              <item>Anything <em>can be</em> in here</item>
              <item>Or <em>also</em> in here</item>
          </slide>
    EOF

    Overview
    Anything
    can be
    Or
    also




.. code-block:: toml

    [[command]]
        name="xpath"
        help = "Find xml elements matching xpath query."
        arguments = [{name="query", type="str"}]
        inject_values=["query"]

        [[command.stages]]
        command = "map"

        [[command.stages]]
        command = "map"
        params = {code="x.encode() ! io.BytesIO ! lxml.etree.parse ! x.findall(query) ! list" }

        [[command.stages]]
        command="chain"


Generate json objects
++++++++++++++++++++++

.. code-block:: bash

    % mario jo 'name=Alice age=21 hobbies=["running"]'
    {"name": "Alice", "age": 21, "hobbies": ["running"]}


.. code-block:: toml

    [[command]]


        name="jo"
        help="Make json objects"
        arguments=[{name="pairs", type="str"}]
        inject_values=["pairs"]

        [[command.stages]]
        command = "eval"
        params = {code="pairs"}

        [[command.stages]]
        command = "map"
        params = {code="shlex.split(x, posix=False)"}

        [[command.stage]]
        command = "chain"

        [[command.stages]]
        command = "map"
        params = {code="x.partition('=') ! [x[0], ast.literal_eval(re.sub(r'^(?P<value>[A-Za-z]+)$', r'\"\\g<value>\"', x[2]))]"}

        [[command.stages]]
        command = "apply"
        params = {"code"="dict"}

        [[command.stages]]
        command = "map"
        params = {code="json.dumps"}



Read csv file
+++++++++++++

Read a csv file into Python dicts. Given a csv like this:


.. code-block:: bash

    % cat names.csv
    name,age
    Alice,21
    Bob,25

try:

.. code-block:: bash

    % mario csv < names.csv
    {'name': 'Alice', 'age': '21'}
    {'name': 'Bob', 'age': '25'}


.. code-block:: toml

    base_exec_before = '''
    import csv
    import typing as t


    def read_csv(
        file, header: bool, **kwargs
    ) -> t.Iterable[t.Dict[t.Union[str, int], str]]:
        "Read csv rows into an iterable of dicts."

        rows = list(file)

        first_row = next(csv.reader(rows))
        if header:
            fieldnames = first_row
            reader = csv.DictReader(rows, fieldnames=fieldnames, **kwargs)
            return list(reader)[1:]

        fieldnames = range(len(first_row))
        return csv.DictReader(rows, fieldnames=fieldnames, **kwargs)

    '''




    [[command]]
        name = "csv"
        help = "Load csv rows into python dicts. With --no-header, keys will be numbered from 0."
        inject_values=["delimiter", "header"]

        [[command.options]]
        name = "--delimiter"
        default = ","
        help = "field delimiter character"

        [[command.options]]
        name = "--header/--no-header"
        default=true
        help = "Treat the first row as a header?"

        [[command.stages]]
        command = "apply"
        params = {code="read_csv(x, header=header, delimiter=delimiter)"}

        [[command.stages]]
        command = "chain"

        [[command.stages]]
        command = "map"
        params = {code="dict(x)"}






.. _command-config-schema:

Command configuration schema
--------------------------------

At the top level, add new commands with a ``[[command]]`` heading, documented as ``CommandSpecschema`` in the tables.

.. marshmallow:: mario.declarative:CommandSpecSchema
