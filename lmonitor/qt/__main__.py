import os
import sys

# Also works when Windows starts this file directly (the admin relaunch does
# that): put the project folder on the import path first.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lmonitor.qt.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
