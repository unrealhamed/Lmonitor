"""v1.18.4 - Network usage: an easy hour list.

The author could not tell how much was used "today at 4": the hour chart had no numbers
and labels only every 3 hours. Now the chosen day is a list - one row per hour that had
traffic, in time order: "16:00 - 17:00", "4 PM" (Persian: "4 بعدازظهر"), the amount, a bar,
download / upload; the current hour says "now"; a click on a row lists its programs."""
import os as _os, sys, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

import lmonitor.engine as E
from lmonitor.backend import Backend
b = Backend()
MB = 1 << 20
now = time.time()
day = E.NetUsage.day_start(now)
lt = time.localtime(now)
h = lambda k: time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, k, 0, 0, 0, 0, -1))
b.net_usage.rows = [(h(16), "game.exe", 100 * MB, 20 * MB), (h(9), "chrome.exe", 10 * MB, 0),
                    (h(16), "chrome.exe", 30 * MB, 0)]
b.net_usage.loaded, b.net_usage.newest = now, now
v = b.net_usage_view(1)
rows = v["usedHours"]
chk("one row per hour with traffic, in time order", [r["h"] for r in rows] == [9, 16])
r16 = rows[1]
chk("hour 16: range, clock and amount in plain text",
    r16["range"] == "16:00 - 17:00" and r16["clock"] == "4 PM" and r16["text"] == "150.0 MB"
    and r16["down"] == "130.0 MB" and r16["up"] == "20.0 MB" and r16["frac"] == 1.0)
chk("9 AM", rows[0]["clock"] == "9 AM" and rows[0]["range"] == "09:00 - 10:00")
chk("the current hour is marked 'now'", all(r["now"] == (r["h"] == lt.tm_hour) for r in rows))
v16 = b.net_usage_view(1, hour=16)
chk("click on 16:00: its programs", [a["name"] for a in v16["apps"]] == ["game.exe", "chrome.exe"])
b.settings.data["language"] = "fa"
chk("Persian parts of the day", b._clock_text(16) == "4 بعدازظهر" and b._clock_text(9) == "9 صبح"
    and b._clock_text(0) == "12 بامداد" and b._clock_text(12) == "12 ظهر" and b._clock_text(21) == "9 شب")
b.settings.data["language"] = "en"
chk("12 AM / 12 PM", b._clock_text(0) == "12 AM" and b._clock_text(12) == "12 PM")
page = open(_os.path.join(ROOT, "lmonitor", "qt", "qml", "pages", "NetUsagePage.qml"), encoding="utf-8").read()
chk("the page shows the list (no hour chart any more)", "usedHours" in page and "hourPlot" not in page
    and 'Tr.t("Whole day")' in page)
fa = open(_os.path.join(ROOT, "lmonitor", "qt", "qml", "Lmonitor", "fa.js"), encoding="utf-8").read()
chk("Persian texts", '"Whole day":' in fa and '"Hours of this day - click one to see its programs":' in fa)
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
