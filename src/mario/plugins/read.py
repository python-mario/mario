"""Functions for read commands."""

import csv
import typing as t


def read_csv_dicts(file, **kwargs) -> t.Iterable[t.Mapping[t.Any, str]]:
    """Read csv rows into an iterable of dicts."""
    rows = list(file)

    first_row = next(csv.reader(rows))

    fieldnames = first_row
    reader = csv.DictReader(rows, fieldnames=fieldnames, **kwargs)
    return list(reader)[1:]


def read_csv_tuples(file, **kwargs) -> t.Iterable[t.Tuple]:
    """Read csv rows into an iterable of tuples."""
    return (tuple(row) for row in csv.reader(file, **kwargs))
