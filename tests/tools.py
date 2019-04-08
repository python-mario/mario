import sys
import subprocess


def run(args, **kwargs):
    args = [sys.executable, "-m", "pype"] + args
    return subprocess.check_output(args, **kwargs)
