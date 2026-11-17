"""v1.18.5 - real-time charts: no hole after Graph overlay page -> another page -> Graphs.

Seen in the author's screen recording. Measured: the last reading came when the Graph
overlay page closed (1.33 s), the next only when Graphs opened again (2.99 s). The
once-a-second reading skipped a turn whenever the last reading was under 0.85 s old - right
after the fast readings of the closed page it skipped, and the 1.7 s hole was over the
1.6 s limit. Now it only skips when the last reading is under 0.4 s old, and a real-time
line joins holes up to 2.5 s (a page change or a busy moment)."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

from lmonitor.backend import Backend
import lmonitor.engine as E
b = Backend()
b.graph_fast = False
for k in ("hud_on", "hud2_on"):
    b.settings.data[k] = False
b.sample()
n0 = len(b.hud_hist.data)
b._hud_t = time.time() - 0.6               # a fast reading of the page that just closed
b.sample()
chk("a reading 0.6 s after the last fast one is not skipped", len(b.hud_hist.data) == n0 + 1)
b._hud_t = time.time() - 0.1
b.sample()
chk("but not two readings at once", len(b.hud_hist.data) == n0 + 1)

# a 2 s hole (old reading, nothing, new reading) is joined in the real-time line
from lmonitor.graphs import GraphHistory
now = time.time()
b.hud_hist = GraphHistory(keys=b.HUD_KEYS, keep=330)
for t in (now - 6, now - 5.75, now - 5.5, now - 3.5, now - 3.25, now - 3, now - 1, now - 0.5, now):
    b.hud_hist.add({"c_use": 10.0}, None, t)
s = b.graph_series(0)
vals = s["c_use"]
first = next(i for i, v in enumerate(vals) if v is not None)
chk("a 2 s hole is joined", all(v is not None for v in vals[first:]))
chk("version 1.18.5 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 18, 5))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
