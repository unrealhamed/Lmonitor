"""v1.18.3 - Network usage: Lmonitor's own count for the hours Windows has not written yet.

Windows writes its usage records about once an hour and sometimes hours late (seen on the
author's PC: the newest record was 11 hours old). Lmonitor now reads the real adapters'
byte counters once a minute, keeps 5-minute totals in netmeter.db, and the Network usage
page shows them after Windows' newest record (totals only, no per-program split)."""
import os as _os, sys, tempfile, time, shutil
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, _os.path.join(ROOT, "tests", "stubs"))

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

import lmonitor.engine as E
IF = E.IfInfo
state = {}
def read():
    return {n: IF(n, r, s, True, 1000, hw) for n, (r, s, hw) in state.items()}

d = tempfile.mkdtemp(prefix="meter_")
try:
    m = E.NetMeter(_os.path.join(d, "netmeter.db"), read)
    t0 = 1_800_000_000.0                      # a slot boundary (divisible by 300)
    MB = 1 << 20
    state.update({"Wi-Fi": (100 * MB, 10 * MB, True), "VPN": (500 * MB, 50 * MB, False)})
    m.tick(t0)                                # first reading: only the start point
    chk("the first reading counts nothing", m.slots(0) == [])
    state.update({"Wi-Fi": (130 * MB, 12 * MB, True), "VPN": (900 * MB, 90 * MB, False)})
    m.tick(t0 + 60)
    chk("real adapter counted, VPN adapter not", m.slots(0) == [(int(t0), 30 * MB, 2 * MB)])
    state["Ethernet"] = (5000 * MB, 0, True)  # plugged in: counted from the next reading
    state["Wi-Fi"] = (5 * MB, 1 * MB, True)   # counter started again (reconnect): skipped once
    m.tick(t0 + 120)
    chk("new adapter / restarted counter add nothing", m.slots(0) == [(int(t0), 30 * MB, 2 * MB)])
    state.update({"Wi-Fi": (15 * MB, 1 * MB, True), "Ethernet": (5004 * MB, 1 * MB, True)})
    m.tick(t0 + 330)                          # next 5-minute slot; >= 300 s since start: saved
    chk("next slot", m.slots(0) == [(int(t0), 30 * MB, 2 * MB), (int(t0) + 300, 14 * MB, 1 * MB)])
    m2 = E.NetMeter(_os.path.join(d, "netmeter.db"), read)
    chk("saved in netmeter.db (a new start reads them back)", m2.slots(0) == m.slots(0))
    m.flush(t0 + 400)
    chk("saving twice does not double", E.NetMeter(_os.path.join(d, "netmeter.db"), read).slots(0) == m.slots(0))
    m.flush(t0 + 63 * 86400)
    chk("older than 62 days removed", E.NetMeter(_os.path.join(d, "netmeter.db"), read).slots(0) == [])

    # ---- merged into the usage view after Windows' newest record
    m3 = E.NetMeter(_os.path.join(d, "m3.db"), read)
    now = time.time()
    base = int(now // 300) * 300
    with m3._lock:
        m3._pending = {base - 7200: [7 * MB, 0], base - 600: [3 * MB, 1 * MB], base: [2 * MB, 0]}
    nu = E.NetUsage(m3)
    lt = time.localtime(base - 3600)
    hr = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, 0, 0, 0, 0, -1))
    nu.rows, nu.newest, nu.loaded = [(hr, "game.exe", 50 * MB, 0)], base - 3600, now
    hours, progs = nu.day(nu.day_start(base))
    live = [p for p in progs if p["name"] == E.NetUsage.LIVE]
    # just after midnight the slot of 10 minutes ago belongs to yesterday: then only today's part counts
    midnight = nu.day_start(base - 600) != nu.day_start(base)
    chk("after Windows' newest record: Lmonitor's count shows as its own row",
        live and ((live[0]["down"] == 5 * MB and live[0]["up"] == 1 * MB) or (midnight and live[0]["down"] == 2 * MB)))
    chk("before it: only Windows' records (nothing counted twice)",
        sum(p["down"] for p in progs) == 55 * MB or nu.day_start(base - 7200) != nu.day_start(base))
    chk("day totals include it", nu.days(1)[0]["down"] >= (2 if midnight else 5) * MB)
finally:
    shutil.rmtree(d, ignore_errors=True)

back = open(_os.path.join(ROOT, "lmonitor", "backend.py"), encoding="utf-8").read()
bridge = open(_os.path.join(ROOT, "lmonitor", "qt", "bridge.py"), encoding="utf-8").read()
chk("the meter starts with the window's bridge and stops (saves) at exit",
    "self._b.net_meter.start()" in bridge and "self.net_meter.stop()" in back)
chk("once a minute, 5-minute slots, 62 days", E.NetMeter.EVERY == 60 and E.NetMeter.SLOT == 300
    and E.NetMeter.KEEP == 62 * 86400)
fa = open(_os.path.join(ROOT, "lmonitor", "qt", "qml", "Lmonitor", "fa.js"), encoding="utf-8").read()
chk("Persian texts", '"Measured by Lmonitor":' in fa and '"After that: measured by Lmonitor (totals only).":' in fa)
chk("version 1.18.3 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 18, 3))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
