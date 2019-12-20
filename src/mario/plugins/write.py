"""Functions for write commands."""

from __future__ import annotations

import csv
import io
import itertools
import typing as t

import yaml


def write_csv_dicts(rows: t.Iterable[t.Dict], header: bool, dialect: str) -> str:
    """Write iterable of dicts to csv."""
    file = io.StringIO()

    iterator = iter(rows)
    first_row = next(iterator)
    fieldnames = list(first_row.keys())
    writer = csv.DictWriter(file, fieldnames=fieldnames, dialect=dialect)
    if header:
        writer.writeheader()
    writer.writerows(itertools.chain([first_row], iterator))

    return file.getvalue()


async def write_csv_tuples(rows: t.AsyncIterable[t.Tuple], dialect: str) -> str:
    """Write tuples to csv.

mario map 'str.split  '  apply list write-csv-tuples async-chain  <<EOF
-rw-r-----  1 tmp  tmp  1.6K Dec 16 22:22 example.py
-rw-r-----  1 tmp  tmp   150 Dec 17 13:08 foo.py
-rw-r-----  1 tmp  tmp   427 Dec 17 11:49 bar.py
EOF
-rw-r-----,1,tmp,tmp,1.6K,Dec,16,22:22,example.py
-rw-r-----,1,tmp,tmp,150,Dec,17,13:08,foo.py
-rw-r-----,1,tmp,tmp,427,Dec,17,11:49,bar.py

"""
    async for row in rows:
        file = io.StringIO()
        writer = csv.writer(file, dialect)
        writer.writerow(row)
        yield file.getvalue()[:-1]


def write_yaml(data) -> str:
    """Write data to yaml string."""
    file = io.StringIO()
    yaml.dump(data, file)
    return file.getvalue()
