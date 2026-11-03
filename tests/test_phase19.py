import os as _os
import sys, io, contextlib, time, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load()
sys.modules["tkinter"] = None
from lmonitor.backend import Backend
from lmonitor import engine as E
b = Backend()
b.sample()
# --- recorder reuses the telemetry reading and keeps one point per STEP
n0 = len(b.recorder.data)
for _ in range(5): b.sample()
chk("recorder keeps one point per 5 s (not one per sample)", len(b.recorder.data) - n0 <= 1)
b.recorder._last = 0; b.recorder.tick({"c_use": 1, "r_use": 2, "g_use": 3})
chk("recorder.tick(snap) stores the given values without reading again", b.recorder.data[-1][1:] == (1, 2, 3))
# --- overlay readings are throttled to the refresh interval
calls = []
orig = b.overlay_model.system
b.overlay_model.system = lambda need=None: (calls.append(1), orig(need))[1]
b.settings.data["show"]["g_use"] = True
b.overlay_model.need = lambda: {"GPU": True}      # no PresentMon on this machine
b.overlay_changed()
for _ in range(5): b.overlay_read()
chk("overlay sensors are read once per refresh interval, not on every call", len(calls) == 1)
b.overlay_changed(); b.overlay_read()
chk("a settings change forces a fresh read", len(calls) == 2)
# --- sensor library update throttle
cr = b.cpu
class H:                                    # fake host: counts Update() calls
    n = 0
    class hw:
        @staticmethod
        def Update(): H.n += 1
    cpu_hw = hw; cpu_temp = cpu_power = None; cpu_clocks = []
    @staticmethod
    def value(x): return None
    @staticmethod
    def positive(x): return None
real = cr.host; cr.host = H(); cr._upd = 0
for _ in range(6): cr.read(True, True, True)
cr.host = real
chk("CpuReader asks the sensor library for an update at most once per MIN_UPDATE", H.n == 1)
# --- tool pages: plain data
for name in ("diag", "opt", "storage", "reports", "sessions"):
    d = getattr(b, "tools_" + name)()
    json.dumps(d, default=str)
    chk(f"tools_{name}() is plain data", isinstance(d, dict))
d = b.tools_diag()
chk("diagnostics data has the fields the page reads", {"running", "progress", "has", "when", "summary", "issues"} <= set(d))
iss = [{"id": "x", "area": "Power", "title": "t", "sev": "info", "evidence": ["e"], "explain": "x", "fix": "y",
        "open": "control powercfg.cpl"},
       {"id": "z", "area": "Drivers", "title": "t2", "sev": "ok", "evidence": [], "explain": "", "fix": "", "open": None}]
b.scanner.issues = iss; b.scanner.when = time.time(); b.scanner.summary = {"info": 1, "ok": 1}
td = b.tools_diag()["issues"]
chk("diagnostic issues carry a Windows page to open and a page Lmonitor can fix it in",
    td[0]["open_text"] == "Open Power Options" and td[0]["goto"] == "Optimizer" and td[1]["open"] == "" and td[1]["goto"] == "")
o = b.tools_opt()
chk("optimizer data: presets for gaming and balanced", [p["name"] for p in o["presets"]] == ["gaming", "balanced"])
s = b.tools_storage()
chk("storage data lists the known cache folders", len(s["caches"]) >= 6 and all("title" in c for c in s["caches"]))
chk("sessions data has status and items", "status" in b.tools_sessions() and isinstance(b.tools_sessions()["items"], list))
# --- sections() groups rows like the Hardware page
sec = b.sections([("head", "A"), ("row", "x", "1"), ("row", "y", "2", "#ff0000"), ("head", "B"), ("bar", "z", "3", 0.5)])
chk("sections() groups head/row/bar rows", [x["title"] for x in sec] == ["A", "B"] and sec[0]["rows"][1]["c"] == "#ff0000" and sec[1]["rows"][0]["c"] == 0.5)
# --- a saved session shows up with a detail view
store = b.session_store
store.path = _os.path.join(__import__("tempfile").gettempdir(), "_lm_sessions.db")
import os
if os.path.exists(store.path): os.remove(store.path)
summ = {"game": "TestGame.exe", "start": time.time() - 900, "end": time.time() - 100, "duration": 800.0,
        "samples": 10, "cpu_name": "cpu", "gpu_name": "gpu", "avg_fps": 99.0, "low1": 70.0, "low01": 50.0, "frames": 1000,
        "c_use": [30, 60], "g_use": [80, 99], "ram": [40, 50], "c_temp": [50, 70], "g_temp": [60, 75],
        "c_clk": [3000, 4000], "g_clk": [1500, 1800], "vram_peak": 3.0, "vram_total": 8.0, "c_approx": False,
        "gpu_status": "ok", "cpu_status": "ok", "mem_status": "ok", "findings": [], "drops": [], "apps": []}
sid = store.save(summ, {k: [] for k in E.SessionRecorder.KEYS})
ts = b.tools_sessions()
chk("a saved session is listed with FPS", len(ts["items"]) == 1 and ts["items"][0]["avg_fps"] == 99.0)
det = b.session_detail(sid)
chk("session detail has sections with rows", len(det) >= 3 and sum(len(x["rows"]) for x in det) > 8)
store.delete([sid]); os.remove(store.path)
# --- ensure_fps starts / stops only when needed, with a retry delay
started = []
b.fps.start = lambda: started.append(1)
b.fps.stop = lambda: started.append(0)
b.settings.data["sessions_on"] = False
b._fps_try = 0
b.ensure_fps(True); b.ensure_fps(True)
chk("PresentMon start is retried at most every 10 s", started == [1])
b.close()
print(f"phase19: {ok} ok, {bad} failed")
