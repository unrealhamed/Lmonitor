"""v1.18.2 - Network usage history (Home > click Network).

How much was downloaded / uploaded in the last 1 / 15 / 30 days, per day, per hour and per
program. The numbers come from Windows' own records (System Resource Usage Monitor, the
source of Settings > Network > Data usage), read from a copy of
C:\\Windows\\System32\\sru\\SRUDB.dat only while the view is open. Only real adapters
count, so traffic through a VPN is not counted twice."""
import os as _os, sys, struct, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

import lmonitor.engine as E
NU = E.NetUsage

# ---- program names as Windows stores them
u = lambda s: s.encode("utf-16-le")
chk("a program path becomes its file name",
    NU.app_name(u("\\device\\harddiskvolume4\\program files\\google\\chrome\\application\\chrome.exe"), 0) == "chrome.exe")
chk("no name = Windows itself", NU.app_name(None, 0) == NU.SYSTEM and NU.app_name(b"", 0) == NU.SYSTEM)
chk("a Store app gets its short name",
    NU.app_name(u("Microsoft.WindowsStore_22609.1401.13.0_x64__8wekyb3d8bbwe"), 1) == "Microsoft Store"
    and NU.app_name(u("Claude_5.11492.5.0_x64__pzs8sxrjxfjjc"), 1) == "Claude")
chk("Windows Update gets a readable name", NU.app_name(u("DoSvc"), 1).startswith("Windows Update"))
chk("'!!svchost.exe!...' -> svchost.exe", NU.app_name(u("!!svchost.exe!2045/05/31:04:32"), 0) == "svchost.exe")

# ---- adapters: the type is in the top 16 bits of the LUID
luid = lambda iftype, idx=1: struct.pack("<Q", (iftype << 48) | (idx << 24))
chk("Ethernet / Wi-Fi count, VPN / loopback / tunnel do not",
    not NU.is_virtual(luid(6)) and not NU.is_virtual(luid(71)) and NU.is_virtual(luid(53))
    and NU.is_virtual(luid(24)) and NU.is_virtual(luid(131)))

# ---- parsing: OLE date (UTC), hour buckets, sums
def ole(t): return struct.pack("<d", t / 86400.0 + 25569.0)
now = time.time()
lt = time.localtime(now)
noon = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 12, 0, 0, 0, 0, -1))
ids = [{"IdType": b"\x00", "IdIndex": struct.pack("<i", 10), "IdBlob": u("\\device\\x\\game.exe")},
       {"IdType": b"\x00", "IdIndex": struct.pack("<i", 11), "IdBlob": None},
       {"IdType": b"\x03", "IdIndex": struct.pack("<i", 12), "IdBlob": b"\x01\x02"}]
def row(t, app, down, up, lu=luid(71)):
    return {"TimeStamp": ole(t), "AppId": struct.pack("<i", app), "InterfaceLuid": lu,
            "BytesSent": struct.pack("<q", up), "BytesRecvd": struct.pack("<q", down)}
MB = 1 << 20
net = [row(noon + 600, 10, 100 * MB, 5 * MB),            # written 12:10 -> the hour 11:00
       row(noon + 600, 11, 20 * MB, 1 * MB),
       row(noon + 600, 10, 999 * MB, 0, luid(53)),        # the same traffic on the VPN adapter
       row(noon + 4200, 10, 50 * MB, 0),                  # written 13:10 -> 12:00
       row(noon - 86400 + 600, 10, 7 * MB, 0)]            # yesterday
rows, newest = NU.parse(net, ids)
chk("OLE dates read right", abs(newest - (noon + 4200)) < 1)
chk("VPN adapter left out (no double count)", sum(r[2] for r in rows) == (100 + 20 + 50 + 7) * MB)
nu = NU()
nu.rows, nu.loaded, nu.newest = rows, now, newest
days = nu.days(15, now=noon)
chk("15 days, today last", len(days) == 15 and days[-1]["down"] == 170 * MB and days[-2]["down"] == 7 * MB)
chk("days before the records are empty, not made up", all(d["down"] == 0 and d["up"] == 0 for d in days[:-2]))
hours, progs = nu.day(days[-1]["start"])
chk("a record counts for the hour before it was written",
    hours[11]["down"] == 120 * MB and hours[12]["down"] == 50 * MB and hours[13]["down"] == 0)
chk("programs of the day, biggest first", [p["name"] for p in progs] == ["game.exe", NU.SYSTEM]
    and progs[0]["down"] == 150 * MB)
_, at12 = nu.day(days[-1]["start"], 12)
chk("programs of one hour", [p["name"] for p in at12] == ["game.exe"] and at12[0]["down"] == 50 * MB)

# ---- the view data (backend)
from lmonitor.backend import Backend
b = Backend()
b.net_usage.rows, b.net_usage.loaded, b.net_usage.newest = rows, now, newest
v = b.net_usage_view(15)
chk("view: 15 bars, newest day chosen", len(v["bars"]) == 15 and v["bars"][-1]["sel"] and v["day"] == v["bars"][-1]["start"])
chk("view: totals as text", v["down"] == "177.0 MB" and v["total"] == "183.0 MB")
chk("view: 24 hours and programs", len(v["hours"]) == 24 and v["apps"][0]["name"] == "game.exe"
    and v["apps"][0]["frac"] == 1.0)
v2 = b.net_usage_view(15, day=v["bars"][-2]["start"], hour=-1)
chk("view: another day can be picked", v2["day"] == v["bars"][-2]["start"] and v2["dayTotal"] == "7.0 MB")
chk("view: an unknown range falls back to 1 day", b.net_usage_view(7)["days"] == 1)
b.settings.data["language"] = "fa"
chk("Persian dates", "نوامبر" in b._date_text(time.mktime((2026, 11, 15, 12, 0, 0, 0, 0, -1)))
    or "ژانویه" in b._date_text(time.mktime((2026, 1, 15, 12, 0, 0, 0, 0, -1))))
b.settings.data["language"] = "en"
nu2 = NU()
real_admin = E.WinApi.is_admin
E.WinApi.is_admin = classmethod(lambda cls: False)
try:
    started = nu2.refresh()
    chk("without admin: says so, reads nothing", not started and nu2.error == "admin")
    b.net_usage = nu2
    chk("view state 'admin'", b.net_usage_view(1)["state"] == "admin")
finally:
    E.WinApi.is_admin = real_admin
chk("read again only after 15 min", NU.MAX_AGE == 900 and "time.time() - self.loaded < self.MAX_AGE" in read("lmonitor", "engine.py"))

# ---- the window
main = read("lmonitor", "qt", "qml", "Main.qml")
page = read("lmonitor", "qt", "qml", "pages", "NetUsagePage.qml")
dash = read("lmonitor", "qt", "qml", "pages", "Dashboard.qml")
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
chk("page in the window, not in the side menu", '"Network usage", src: "pages/NetUsagePage.qml", hidden: true' in main
    and "visible: !modelData.hidden" in main)
chk("Home's Network card opens it", 'page.go("Network usage")' in dash)
chk("1 / 15 / 30 days", '["1 day", "15 days", "30 days"]' in page)
chk("read only while the page is open", "setNetUsageOpen(true)" in page and "setNetUsageOpen(false)" in page)
chk("Persian texts", all('"%s":' % k in fa for k in ("Network usage", "15 days", "Per day - click a day",
                                                      "Programs - whole day", "Click for usage history")))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
