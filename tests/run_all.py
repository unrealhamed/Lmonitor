"""Runs every test script in this folder and prints a summary.

usage:  python tests/run_all.py
The tests use small stand-ins for pynvml / clr (tests/stubs),
so they do not need a GPU, a display or Windows-only drivers.
Needs:  pip install psutil PySide6
"""
import glob
import os
import re
import subprocess
import sys

import tempfile

here = os.path.dirname(os.path.abspath(__file__))
bad = []
# the tests get their own settings folder, so they never touch the real
# %APPDATA%\Lmonitor (settings.json, error.log) of the person running them
env = dict(os.environ, APPDATA=tempfile.mkdtemp(prefix="lmonitor_tests_"), PYTHONIOENCODING="utf-8")
for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
    name = os.path.basename(path)
    try:
        r = subprocess.run([sys.executable, "-u", path], capture_output=True,
                           text=True, timeout=280, cwd=os.path.dirname(here), env=env)
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
