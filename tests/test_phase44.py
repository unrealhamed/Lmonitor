"""v1.21.0 - reliability audit + benchmark, what limited the FPS, history over time.

- Start with Windows: when the taskbar is not ready at sign-in, the tray icon is tried again
  (before: no icon at all - Lmonitor ran invisibly); every start is noted in startup.log.
- error.log no longer stops for good at 200 KB (it starts again), lines carry the date;
  reader errors while Lmonitor closes are not logged.
- Sessions: "Run a benchmark" (one minute of the game in front), what limited the frame rate
  (GPU at full power / spare power / power limit - never "certain" without evidence), the same
  game over time, Windows updates in "what changed", benchmarks only compared with benchmarks.
- PC check report: this PC, its sensors and Lmonitor's own errors. About: delete my history."""
import os as _os, sys, json, time
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

# ================================================================ start with Windows / logs
app = read("lmonitor", "qt", "app.py")
chk("no taskbar yet: the icon is tried again, then the window opens", "retry.setInterval(2000)" in app
    and "tries[0] >= 90" in app and "win.show()" in app)
chk("every start is noted (by Windows / by hand)", 'Logger.note("start", "Lmonitor %s started %s%s"' in app)
E.Logger.MAX = 300
p = E.Paths.LOG_FILE
for i in range(30):
    E.Logger.error("t%d" % i, "line %d %s\n" % (i, "x" * 40))
chk("error.log starts again instead of stopping", _os.path.exists(p[:-4] + ".old.log") and _os.path.getsize(p) < 300 + 200)
chk("error lines carry the date", time.strftime("[%Y-") in open(p, encoding="utf-8").read())
E.Logger.note("start", "test")
chk("startup.log written", "start: test" in open(_os.path.join(E.Paths.CFG_DIR, "startup.log"), encoding="utf-8").read())
b = E.BackgroundReader(lambda: 1 / 0, 1.0, "closing-test")
E.BackgroundReader.stopped = True
before = open(p, encoding="utf-8").read()
b._run_once()
E.BackgroundReader.stopped = False
chk("a reader failing while Lmonitor closes is not logged", "closing-test" not in open(p, encoding="utf-8").read()[len(before) - 50:])

# ================================================================ what limited the frame rate
A = E.SessionAnalyzer
n = 60
def c_with(gu, cu=40, plim=None, fps=100.0):
    c = {k: [None] * n for k in E.SessionRecorder.KEYS}
    c["t"] = [i * 2.0 for i in range(n)]
    c["fps"], c["g_use"], c["c_use"], c["g_plim"] = [fps] * n, [float(gu)] * n, [float(cu)] * n, [plim] * n
    return c
lim = A.limits(c_with(99))
chk("GPU at 99 %: it set the frame rate", lim["gpu_full"] == 1.0 and lim["gpu_spare"] == 0.0)
lim = A.limits(c_with(50, cu=95))
chk("GPU at 50 % with the CPU busy: spare GPU, busy CPU", lim["gpu_spare"] == 1.0 and lim["cpu_busy"] == 1.0)
chk("power limit only from the driver's own signal", A.limits(c_with(99, plim=True))["power"] == 1.0
    and A.limits(c_with(99, plim=None))["power"] is None)
short = {k: v[:10] for k, v in c_with(99).items()}
chk("too little data (20 s): nothing said", A.limits(short)["gpu_full"] is None)
c_none = c_with(99); c_none["fps"] = [None] * n
chk("no frame rate measured: nothing said", A.limits(c_none)["gpu_full"] is None)
R = E.SessionReport
def summ(c, **kw):
    s = A.summarize(c, {"game": "g.exe", "start": 0.0, "end": 120.0}, {"count": 12000, "total_ms": 120000.0, "low1": 60.0})
    s.update(kw)
    return s
nt = R.noticed(summ(c_with(99)))
chk("GPU-bound: told plainly, as information (not a problem)", nt and nt[0]["sev"] == "info"
    and "set the frame rate" in nt[0]["text"])
chk("information alone keeps 'a smooth session'", "smooth" in R.verdict(summ(c_with(99)), nt))
nt = R.noticed(summ(c_with(50, cu=95)))
chk("spare GPU + busy CPU: 'probably' the processor, other reasons listed", nt and "probably" in nt[0]["tip"]
    and "V-Sync" in nt[0]["tip"])
nt = R.noticed(summ(c_with(99, plim=True)))
chk("power limit: 'may have been limited', with what to do", nt[0]["sev"] == "notice" and "may have been limited" in nt[0]["text"])

# ================================================================ benchmark
class FakeFps:
    alive = True
    def __init__(self): self.cur, self.cnt = (77, "game.exe"), [0, 0.0, [0] * 400]
    def current(self): return self.cur
    def counters(self, pid):
        return list(self.cnt) if pid == 77 else None
    def recent(self, pid, within): return pid == 77 and self.cur is not None
class FakeCpu:
    name = "cpu"
    def read(self, *a): return 60.0, 40.0, 4000.0, False
class FakeGpu:
    power_limit = False
    def read(self, want): return 97.0, 70.0, 100.0, 2000.0, (4.0, 8.0)
    def display_name(self): return "gpu"
class Store:
    def __init__(self): self.rows = []
    def save(self, s, c): self.rows.append(s); return len(self.rows)
    def update(self, sid, s, c): self.rows[sid - 1] = s
st, fps = Store(), FakeFps()
rec = E.SessionRecorder(fps, FakeCpu(), FakeGpu(), st, enabled=lambda: False)   # recording itself off
rec.start_bench(1000.0)
chk("benchmark waits for a game", "switch to your game" in rec.status()[0])
t = 1000.0
for i in range(40):
    fps.cnt[0] += 240; fps.cnt[1] += 2000.0
    rec.step(t); t += 2
chk("one minute recorded, saved as a benchmark, recording-off does not stop it",
    len(st.rows) == 1 and st.rows[0]["benchmark"] and 58 <= st.rows[0]["duration"] <= 62)
chk("then it is done and says so", rec.bench is None and rec.bench_done and rec.bench_done[1] == "Benchmark finished")
rec.bench_done = None
rec.start_bench(t)
for i in range(3):
    rec.step(t); t += 2
fps.cur = None
rec.step(t + 30)
chk("game closed early: nothing saved, told why", len(st.rows) == 1 and "closed" in rec.bench_done[1])
rec.start_bench(t); rec.stop_bench()
chk("cancel: back to normal", rec.bench is None)
chk("Lmonitor's own window is never taken for a game", "lmonitor.exe" in E.SessionRecorder.IGNORE)

# ================================================================ compare / over time
a = {"game": "g.exe", "start": 0.0, "duration": 60, "benchmark": True, "avg_fps": 100.0, "windows": "26100.1"}
b2 = dict(a, start=5000.0, avg_fps=110.0, windows="26100.2")
cmp = R.compare(a, b2)
chk("two one-minute benchmarks are compared", cmp["ok"] and "Windows update: build 26100.1 -> 26100.2" in cmp["changed"])
chk("a benchmark is not compared with a normal session", not R.compare(a, dict(b2, benchmark=False, duration=600))["ok"])
hist = [{"avg_fps": 100.0, "g_temp": [70, 80], "c_temp": [60, 75]} for _ in range(3)]
tr = {x["label"]: x for x in R.trend({"avg_fps": 100.0, "g_temp": [70, 86], "c_temp": [60, 75]}, hist)}
chk("over time: GPU 6 °C hotter than usual, FPS the same", tr["GPU hottest"]["text"] == "6 °C higher than usual"
    and tr["GPU hottest"]["better"] is False and tr["Average FPS"]["text"] == "about the same as usual")
chk("over time needs 2 earlier sessions", R.trend({"avg_fps": 1.0}, hist[:1]) == [])
chk("Windows build read for 'what changed'", isinstance(E.windows_build(), str))

# ================================================================ history size, delete, report
chk("200 sessions kept, samples only for the newest 60", E.SessionStore.KEEP == 200 and E.SessionStore.KEEP_SAMPLES == 60)
from lmonitor.backend import Backend
bk = Backend()
bk.session_store.save({"game": "x.exe", "start": time.time(), "duration": 70.0}, {"t": []})
bk.clear_history()
chk("Delete my history: sessions gone", bk.session_store.list() == [])
sy = bk.report_system()
chk("report: this PC, sensors, own errors", all(k in sy for k in ("cpu", "gpu", "gpu_driver", "ram_gb", "windows", "sensors", "errors"))
    and all(v in ("available", "not available", "not supported", "stopped answering", "not running")
            for v in sy["sensors"].values()))
rep = bk.reports.build()
html = E.ReportBuilder.to_html(rep)
chk("report HTML shows This PC and Sensors, no user name in paths", "<h2>This PC</h2>" in html and "<h2>Sensors</h2>" in html
    and E.ReportBuilder.redact(r"C:\Users\Someone\x") == r"C:\Users\<user>\x")
bk.close()

# ================================================================ window + texts
q = lambda *p: read("lmonitor", "qt", "qml", *p)
sess, about = q("pages", "SessionsPage.qml"), q("pages", "About.qml")
chk("Sessions: benchmark button, tag, over time", "tools.benchStart()" in sess and 'Tr.t("Benchmark")' in sess
    and "page.rep.trend" in sess)
chk("About: delete my history (asks first)", "backend.clearHistory()" in about and "ConfirmButton" in about)
fa = q("Lmonitor", "fa.js")
need = ("Run a benchmark", "Cancel benchmark", "Compared with your earlier sessions of this game", "Delete my history",
        "Your graphics card set the frame rate: it worked at full power most of the time.", "What limited your FPS")
miss = [k for k in need if ('"%s":' % k) not in fa]
chk("Persian texts %s" % (miss or ""), not miss)
wn = E.WhatsNew.pending("1.20.2", "1.21.0")
chk("What's new 1.21.0", wn and wn["version"] == "1.21.0" and len(wn["slides"]) == 4)
chk("version 1.21.0 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 21, 0))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
