import pathlib
import subprocess
import sys


TESTS_DIR = pathlib.Path(__file__).parent


def run(args, capture_output=True, check=True, **kwargs):
    args = [sys.executable, "-m", "mario"] + args
    proc = subprocess.run(args, capture_output=capture_output, check=check, **kwargs)
    return proc.stdout
