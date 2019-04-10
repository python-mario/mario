import pathlib
import sys
import subprocess

TESTS_DIR = pathlib.Path(__file__).parent

def run(args, **kwargs):
    args = [sys.executable, "-m", "pype"] + args
    return subprocess.check_output(args, **kwargs)
