import pathlib
import subprocess
import sys


TESTS_DIR = pathlib.Path(__file__).parent


def run(args, **kwargs):
    args = [sys.executable, "-m", "mario"] + args
    return subprocess.check_output(args, **kwargs)
