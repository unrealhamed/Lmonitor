"""Runs every test script in this folder and prints a summary.

usage:  python tests/run_all.py
The tests use small stand-ins for tkinter / pynvml / clr / pystray (tests/stubs),
so they do not need a GPU, a display or Windows-only drivers.
Needs:  pip install psutil pillow
"""
import glob
import os
import re
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
bad = []
for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
    name = os.path.basename(path)
    try:
        r = subprocess.run([sys.executable, "-u", path], capture_output=True,
                           text=True, timeout=280, cwd=os.path.dirname(here))
        out = r.stdout + r.stderr
        failed = (r.returncode != 0 or re.search(r"^FAIL ", out, re.M)
                  or re.search(r"\b[1-9]\d* failed|FAILED: [1-9]|Traceback", out))
    except subprocess.TimeoutExpired:
        out, failed = "timeout", True
    print(("FAILED  " if failed else "ok      ") + name)
    if failed:
        bad.append(name)
print("\n%d test files, %d failed" % (len(glob.glob(os.path.join(here, "test_*.py"))), len(bad)))
sys.exit(1 if bad else 0)
