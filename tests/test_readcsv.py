import csv
import subprocess
import sys


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


def test_py_read():

    for _ in range(10):
        output = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "mario",
                "--exec-before",
                exec_before,
                "map",
                "read_csv_row",
            ],
            input=text.encode(),
        ).decode()

        expected = (
            "None\n{'name': 'alice', 'age': '21'}\n{'name': 'bob', 'age': '22'}\n"
        )
        assert output == expected


def test_apply_csv_dictreader_read_csv():

    for _ in range(10):
        output = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "mario",
                "apply",
                "csv.DictReader ! [dict(y) for y in x]",
            ],
            input=text.encode(),
        ).decode()

        expected = "[{'name': 'alice', 'age': '21'}, {'name': 'bob', 'age': '22'}]\n"

        assert output == expected
