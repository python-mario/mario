===================
Async execution
===================

.. include:: ../README.rst
   :start-after: async-inclusion-start
   :end-before: async-inclusion-end


``async-map`` and ``async-filter`` values are handled in streaming fashion, while retaining the order of the input items in the output. The order of function calls is not constrained -- if you need the function to be **called** with items in a specific order, use the synchronous version.

Making concurrent requests, each response is printed one at a time, as soon as (1) it is ready and (2) all of the preceding requests have already been handled.

For example, the ``3 seconds`` item is ready before the preceding ``4 seconds`` item, but it is held until the ``4 seconds`` is ready because ``4 seconds`` was started first, so the ordering of the input items is maintained in the output.



.. code-block:: bash

    % time mario --exec-before 'import datetime; now=datetime.datetime.utcnow; START_TIME=now(); print("Elapsed time | Response size")' map 'await asks.get !  f"{(now() - START_TIME).seconds} seconds    | {len(x.content)} bytes"'  <<EOF
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
