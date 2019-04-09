import sys
import csv
import io
import subprocess

from typing import Iterable
from typing import Generator
from typing import Dict

import pytest

def make_reader():
    field_names = None

    def read_line(line):
        nonlocal field_names
        print("\t\t\t\t\t", line)
        reader = csv.reader([line])
        row = next(reader)

        if field_names is None:
            field_names = row
            return None

        return dict(zip(field_names, row))

    return read_line


text = """\
name,age
alice,21
bob,22
"""


def test_read_line():
    read = make_reader()

    lines = text.splitlines()

    rows = list(map(read, lines))
    # rows = list(map(dict, csv.DictReader(lines)))
    assert rows == [None, {"name": "alice", "age": "21"}, {"name": "bob", "age": "22"}]


expected = """\
{'bob': 'name', '22': 'age'}
{'bob': 'alice', '22': '21'}
None
"""


exec_before = """\

def make_reader():
    import csv

    field_names = None

    def read_line(line):
        nonlocal field_names
        # print('\t\t\t\t\t', line)
        reader = csv.reader([line])
        row = next(reader)

        if field_names is None:
            field_names = row
            return None

        return dict(zip(field_names, row))

    return read_line

read_csv_row = make_reader()

"""

@pytest.mark.xfail(strict=True)
def test_py_read():

    for _ in range(10):
        output = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "pype",
                "--exec-before",
                exec_before,
                "map",
                "read_csv_row",
            ],
            input=text.encode(),
        ).decode()
        assert output == expected
