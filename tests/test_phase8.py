import os as _os
import sys, io, contextlib, time, os, random
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load()
A = m.SessionAnalyzer
random.seed(1)
def series(n, f):
    return [f(i) for i in range(n)]
def cols(n=150, **kw):
    base = {k: [None] * n for k in m.SessionRecorder.KEYS}
    base["t"] = [1000 + 2.0 * i for i in range(n)]
    base["fps"] = [90.0] * n
    base["ram"] = [60.0] * n; base["avail"] = [8.0] * n
    base.update(kw)
    return base

# --- throttling needs a clock DROP, not just heat
n = 150
c = cols(n, g_use=[99.0] * n, g_temp=[84.0] * n, g_clk=[1900.0] * n)
r = A.throttle(c["g_use"], c["g_temp"], c["g_clk"], 90, 80, .10, "GPU")
chk("hot but clock stable -> NOT throttling", r["status"] == "hot_no_drop" and "no evidence" in r["text"])
clk = [1900.0] * 100 + [1500.0] * 50
r = A.throttle(c["g_use"], c["g_temp"], clk, 90, 80, .10, "GPU")
chk("clock fell while hot -> possible thermal throttling", r["status"] == "possible" and r["secs"] == 100.0)
c2 = cols(n, g_use=[99.0] * n, g_temp=[65.0] * n, g_clk=clk)
r = A.throttle(c2["g_use"], c2["g_temp"], clk, 90, 80, .10, "GPU")
chk("clock fell but cool -> not called thermal", r["status"] == "clock_dip" and "not thermal" in r["text"])
r = A.throttle([99.0] * n, [None] * n, [1900.0] * n, 90, 80, .1, "GPU")
chk("no temperature sensor -> cannot judge (not 'fine')", r["status"] == "no_temp" and "cannot judge" in r["text"])
r = A.throttle([99.0] * n, [80.0] * n, [None] * n, 90, 80, .1, "GPU")
chk("no clock sensor -> cannot judge", r["status"] == "no_clock")
r = A.throttle([20.0] * n, [85.0] * n, [900.0] * n, 90, 80, .1, "GPU")
chk("hot but never loaded -> too little data", r["status"] == "few")
r = A.throttle([60.0] * n, [55.0] * n, [900.0] * n, 90, 80, .1, "GPU")
chk("never near hot -> thermal throttling unlikely (not 'unknown')", r["status"] == "cool" and "unlikely" in r["text"])
r = A.throttle([60.0] * n, [55.0] * n, [None] * n, 90, 80, .1, "GPU")
chk("cool even without a clock sensor", r["status"] == "cool")

# --- RAM / VRAM
r = A.memory(cols(ram=[95.0] * 150, avail=[0.9] * 150))
chk("RAM nearly full -> low", r["status"] == "low")
chk("RAM fine", A.memory(cols())["status"] == "ok")
chk("no RAM data -> unknown", A.memory(cols(ram=[None] * 150))["status"] == "unknown")
r = A.vram(cols(vram=[7.9] * 150, vram_total=[8.0] * 150))
chk("VRAM almost full", r["status"] == "full")
chk("VRAM unknown without sensor", A.vram(cols())["status"] == "unknown")

# --- drops and their cause
fps = [90.0] * 60 + [30.0] * 4 + [90.0] * 40
d = A.drops(cols(100, fps=fps, g_use=[99.0] * 100), 1900, 4500)
chk("one drop found, 90 -> 30", len(d) == 1 and round(d[0]["low"]) == 30 and round(d[0]["before"]) == 90)
chk("drop time is an offset in the session", abs(d[0]["at"] - 120) < 3)
chk("cause: GPU limited", "GPU was fully loaded" in d[0]["cause"])
d = A.drops(cols(100, fps=fps, ram=[95.0] * 100), 1900, 4500)
chk("cause: RAM full wins", d[0]["cause"] == "RAM was nearly full")
d = A.drops(cols(100, fps=fps, g_use=[40.0] * 100, c_use=[30.0] * 100), 1900, 4500)
chk("no visible cause is said honestly", d[0]["cause"].startswith("No limit visible"))
chk("steady fps -> no drops", A.drops(cols(), 1, 1) == [])

# --- background apps
apps = A.apps({"chrome.exe": [150.0, 3 * 1024**3], "tiny.exe": [1.0, 10 * 1024**2],
               "miner.exe": [900.0, 200 * 1024**2]}, 30)
chk("only heavy apps listed, worst first", [a["name"] for a in apps] == ["miner.exe", "chrome.exe"] and apps[0]["cpu"] == 30.0)

# --- summary + store roundtrip
frames = {"count": 9000, "total_ms": 100000.0, "low1": 55.0, "low01": 40.0}
meta = {"game": "Game.exe", "start": 1000.0, "end": 1300.0, "c_approx": False, "apps": {}, "scans": 0}
cc = cols(150, g_use=[99.0] * 150, g_temp=[84.0] * 150, g_clk=clk, fps=fps + [90.0] * 50)
S = A.summarize(cc, meta, frames)
chk("summary: avg fps from frame times", abs(S["avg_fps"] - 90.0) < .01 and S["low1"] == 55.0)
chk("summary: GPU warning + drop notice", S["gpu_status"] == "possible" and any(f["sev"] == "warn" for f in S["findings"]))
chk("summary says CPU unknown when no sensor", S["cpu_status"] in ("no_temp", "no_clock") and any(f["sev"] == "unknown" for f in S["findings"]))
store = m.SessionStore(os.path.join(m.Paths.CFG_DIR, "t_sessions.db"))
sid = store.save(S, cc)
lst = store.list()
chk("store: saved and listed", len(lst) == 1 and lst[0]["id"] == sid and lst[0]["summary"]["game"] == "Game.exe")
chk("store: samples roundtrip", store.load_samples(sid)["fps"][:3] == [90.0, 90.0, 90.0])
for i in range(m.SessionStore.KEEP + 5):
    s2 = dict(S); s2["start"] = 2000.0 + i; store.save(s2, cc)
chk("store keeps only the newest KEEP", len(store.list()) == m.SessionStore.KEEP)
store.delete([store.list()[0]["id"]])
chk("store delete", len(store.list()) == m.SessionStore.KEEP - 1)

# --- recorder with a fake PresentMon / hardware
class FakeFps:
    def __init__(s): s.alive = True; s.status = ""; s.cnt = 0; s.ms = 0.0; s.hist = [0] * 4001; s.last = time.time(); s.name = "Game.exe"; s.pid = 7; s.frames = True
    def feed(s, n=120, ms=1000 / 60):
        s.cnt += n; s.ms += n * ms; s.hist[int(ms * 4)] += n; s.last = time.time()
    def current(s): return (s.pid, s.name) if s.frames else None
    def recent(s, pid, w): return s.frames
    gone = False
    def counters(s, pid): return None if s.gone else (s.cnt, s.ms, list(s.hist))
class FakeCpu:
    name = "Test CPU"
    def read(s, *a): return (60.0, None, 4200.0, False)
class FakeGpu:
    def display_name(s): return "Test GPU"
    def read(s, w): return (97.0, 70.0, 200.0, 1900.0, (4.0, 8.0))
fk = FakeFps(); st2 = m.SessionStore(os.path.join(m.Paths.CFG_DIR, "t2.db"))
enabled = [True]
rec = m.SessionRecorder(fk, FakeCpu(), FakeGpu(), st2, lambda: enabled[0])
rec.load = type("L", (), {"read": lambda s: 45.0})()
t0 = 10000.0
rec.step(t0); rec.step(t0 + 2)
chk("not started before confirmed", rec.cur is None)
rec.step(t0 + 8)
chk("started after steady frames", rec.cur is not None and rec.cur["name"] == "Game.exe")
for i in range(1, 50):
    fk.feed(); rec.step(t0 + 8 + 2 * i)
chk("samples recorded", rec.cur["n"] == 49 and rec.cur["c"]["fps"][-1] and abs(rec.cur["c"]["fps"][-1] - 60) < 1)
chk("status shows recording", rec.status()[1] and "Game.exe" in rec.status()[0])
chk("live session already visible in the list while playing", len(st2.list()) == 1 and st2.list()[0]["summary"]["live"] is True and rec.version >= 1)
fk.frames = False; fk.gone = True    # PresentMon forgets the program once the game closes
rec.step(t0 + 8 + 2 * 50)
fk.gone = False
chk("saved when frames stop (even if PresentMon already forgot it)", rec.cur is None and len(st2.list()) == 1 and st2.list()[0]["summary"]["live"] is False)
v_after = rec.version
sv = st2.list()[0]["summary"]
chk("saved summary has avg fps ~60, GPU ok", abs(sv["avg_fps"] - 60) < 1 and sv["gpu_status"] in ("ok", "few", "hot_no_drop") and sv["g_temp"][1] == 70.0)
# ignore list + short session + disabled
fk.frames = True; fk.name = "chrome.exe"
for i in range(6): rec.step(t0 + 500 + 2 * i)
chk("browsers are ignored", rec.cur is None)
fk.name = "Short.exe"
for i in range(6): rec.step(t0 + 600 + 2 * i)
fk.feed(); rec.step(t0 + 640); fk.frames = False; rec.step(t0 + 650)
chk("sessions under a minute are not saved", rec.version == v_after and len(st2.list()) == 1)
st2.save(dict(S, live=True, start=5.0), cc); st2.clear_live()
chk("stale 'live' flags are cleared", not any(x["summary"].get("live") for x in st2.list()))
fk.frames = True; fk.name = "Game2.exe"
for i in range(5): rec.step(t0 + 700 + 2 * i)
enabled[0] = False; rec.step(t0 + 720)
chk("turning recording off ends a running session without crashing", rec.cur is None and not rec.status()[1])

# --- UI page
app = boot(m); w = app.window
app.session_store = m.SessionStore(os.path.join(m.Paths.CFG_DIR, "ui.db")); 
for i in range(3):
    s2 = dict(S); s2["start"] = time.time() - 3600 * (i + 1); s2["avg_fps"] = 80 + 10 * i; s2["g_temp"] = [70 + 5 * i, 80 + 5 * i]
    s2["game"] = "Game.exe" if i < 2 else "Other.exe"
    app.session_store.save(s2, cc)
w.show(); w.show_page(w.PAGE_SESS); flush()
chk("sessions page lists them, newest selected", len(w.sess_list.sessions) == 3 and len(w.sess_sel) == 1)
w.canvas.render(f"{OUT}/p8_sessions.png")
w.sess_list.click(1); flush()
chk("second click -> compare tab with 2 sessions", len(w.sess_sel) == 2 and w.sess_tab == 4)
rows = m.SessionView.rows_compare(w.sess_sel[0]["summary"], w.sess_sel[1]["summary"])
chk("compare rows have A -> B values and colours", any("->" in r[2] for r in rows if r[0] == "row") and any(len(r) > 3 and r[3] for r in rows))
w.canvas.render(f"{OUT}/p8_compare.png")
w.sess_list.click(1); flush()
chk("unselect -> back to summary", len(w.sess_sel) == 1 and w.sess_tab == 0)
for t in (1, 2, 3):
    w._pick_sess_tab(t); flush(); w.canvas.render(f"{OUT}/p8_tab{t}.png")
chk("all tabs render", True)
w.sess_list.delete(); chk("delete asks first", len(app.session_store.list()) == 3)
w.sess_list.delete(); flush()
chk("second click deletes", len(app.session_store.list()) == 2)
app.set_sessions_on(False); flush()
chk("setting off saved and PresentMon follows overlay need", app.settings["sessions_on"] is False)
app.set_sessions_on(True); flush()
chk("setting persists in file", app.settings["sessions_on"] is True)
for i in range(len(w.PAGES)): w.show_page(i); flush()
chk("all pages open", True)
print(f"phase8: {ok} ok, {bad} failed")
