import os as _os
import sys, io, contextlib, time, subprocess, textwrap, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
# 1) the engine never imports a UI toolkit
src = open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lmonitor", "engine.py")).read() + open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lmonitor", "backend.py")).read()
import re
chk("engine/backend import no tkinter, PIL, pystray or Qt at module level",
    not re.search(r"^(import|from)\s+(tkinter|PIL|pystray|PySide6|PyQt)", src, re.M))
# 2) headless backend with tkinter blocked
m = load()
sys.modules["tkinter"] = None   # any later 'import tkinter' now fails
from lmonitor.backend import Backend
b = Backend()
chk("Backend builds without any window", b.settings is not None and b.telemetry is not None)
chk("before the first sample the dashboard says not ready", b.dashboard() == {"ready": False})
b.sample()
d = b.dashboard()
chk("after a sample: cards, network, status, perf are there", d["ready"] and set(d["cards"]) == {"cpu", "gpu", "ram", "disk"} and "perf" in d and "status" in d)
json.dumps(d, default=float)
chk("dashboard data is plain (JSON friendly)", True)
for k in ("cpu", "gpu", "ram"):
    c = d["cards"][k]
    chk(f"{k}: status is a known word", c["status"] in ("ok", "warm", "hot", "high", "none"))
b.telemetry.snap["c_temp"] = None; b.telemetry.snap["c_use"] = None
d = b.dashboard()
chk("missing CPU data -> None + status none, no invented value", d["cards"]["cpu"]["use"] is None and d["cards"]["cpu"]["status"] == "none" and d["status"]["cpu_sensor"] is False)
chk("card status rules", m.CardStatus.heat(50, 85, 80) == "hot" and m.CardStatus.heat(95, 40, 80) == "high" and m.CardStatus.heat(50, 72, 80) == "warm" and m.CardStatus.ram(85) == "warm" and m.CardStatus.disk(5) == "full" and m.CardStatus.disk(15) == "low" and m.CardStatus.disk(50) == "ok")
chk("every perf range returns 3 series", all(len(b.perf(i)) == 3 for i in range(4)))
# ---- overlay data + settings through the backend
m.WinApi.setup()
b.settings.reset(); b.sample()
v = b.overlay_view(b.overlay_read())
names = [g["name"] for g in v["groups"]]
chk("overlay view: groups in the user's order, all items shown by default", names == ["FPS", "GPU", "CPU", "RAM", "NET"] and all(g["items"] for g in v["groups"]))
b.set_show("g_temp", False); b.set_show("graph", False)
b.set_order({"groups": ["NET", "CPU"], "items": {}})
v = b.overlay_view(b.overlay_read())
chk("hidden items vanish; a saved order is applied (missing groups appended)", [g["name"] for g in v["groups"]][:2] == ["NET", "CPU"] and "g_temp" not in [i["key"] for g in v["groups"] for i in g["items"]])
chk("unknown metric key refused", b.set_show("nope", True) is False)
texts = {"g_use": ("90%", "#ff0000"), "c_use": ("5%", None)}
b.settings.reset(); b.set_setting("value_color", "amber")
v = b.overlay_view(texts)
cols = {i["key"]: i["color"] for g in v["groups"] for i in g["items"]}
chk("warning colors are kept, normal values use the chosen value color", cols["g_use"] == "#ff0000" and cols["c_use"] == b.value_hex() and b.value_hex() != "#ffffff")
chk("missing reading shows --, never a number", {i["key"]: i["text"] for g in v["groups"] for i in g["items"]}["g_temp"] == "--")
b.settings.reset()
chk("settings go through the engine's validation", b.set_setting("text", 99) and b.settings["text"] == 18 and b.set_setting("pos", "evil") and b.settings["pos"] == "left" and b.set_setting("bogus", 1) is False)
chk("hardware tabs and charts are plain data", all(isinstance(b.hardware(i), list) for i in range(6)) and len(b.charts()) == 5)
cols = b.hardware_sections(0)
chk("hardware sections: two columns of {title, rows}", len(cols) == 2 and all(isinstance(x["title"], str) and isinstance(x["rows"], list) for c in cols for x in c) and sum(len(c) for c in cols) >= 2)
chk("every hardware tab splits into sections without error", all(len(b.hardware_sections(i)) == 2 for i in range(6)))
chk("dashboard carries names for the new header", isinstance(d["pc"], str) and isinstance(d["user"], str) and "name" in d["cards"]["cpu"] and "name" in d["cards"]["gpu"])
chk("backend gives the chart interval and a CPU note", b.interval_ms() >= 250 and isinstance(d["cards"]["cpu"]["note"], str))
chk("CPU note names the real reason when temperature is missing", b._cpu_note(None) != "" and b._cpu_note(55.0) == "")
import os
chk("resources (DLL, PresentMon) are looked up next to monitor.py, not inside the package",
    os.path.dirname(m.Paths.LHM_DLL if hasattr(m, "Paths") else __import__("lmonitor.engine").engine.Paths.LHM_DLL) == _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
json.dumps(b.settings_view(), default=str)
chk("settings view is JSON friendly", True)
b.close(); chk("close() does not raise", True)
chk("no tkinter was imported by the backend", sys.modules.get("tkinter") is None)
print(f"phase18: {ok} ok, {bad} failed")
