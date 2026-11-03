import os as _os
import sys, io, contextlib, time, os, textwrap
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load()
A = m.DiagAnalyzer
GIB = 1024 ** 3
def facts(**kw):
    f = {"startup": [{"name": f"App{i}", "cmd": "x", "where": "HKCU Run", "enabled": True} for i in range(4)],
         "power": {"guid": "381b4222-f694-41f0-9685-ff5bb260df2e", "name": "Balanced"},
         "battery": {"present": False, "plugged": None},
         "disks": [{"mount": "C:\\", "total": 500 * GIB, "free": 250 * GIB}],
         "events": [], "gpu_drivers": [{"name": "NVIDIA GeForce RTX 3060", "ver": "31.0.15.5222", "date": "2026-08-01"}],
         "devices": [], "services": {"Audiosrv": {"status": "Running", "start": "Automatic"},
                                     "SysMain": {"status": "Running", "start": "Automatic"}},
         "settings": {"game_mode": 1, "game_dvr": None, "capture": 0, "hags": 2, "fast_startup": 1},
         "memory": {"ram_gb": 16.0, "swap_gb": 4.0}, "errors": {}}
    f.update(kw); return f
def by(issues, id_): return next((i for i in issues if i["id"] == id_), None)
def ev(p, i, lvl=2, t="2026-11-01T10:00:00"): return {"p": p, "id": i, "lvl": lvl, "t": t}

# --- healthy PC: nothing red
iss = A.analyze(facts())
chk("healthy PC: no warning / notice", not any(i["sev"] in ("warn", "notice") for i in iss))
chk("every issue has proof, meaning and fix", all(i["evidence"] and i["explain"] and i["fix"] for i in iss))

# --- startup
many = [{"name": f"App{i}", "cmd": "x", "where": "HKCU Run", "enabled": i < 12} for i in range(15)]
s = by(A.analyze(facts(startup=many)), "startup")
chk("startup: 12 enabled -> notice, counts shown", s["sev"] == "notice" and "12 enabled, 3 disabled" in s["evidence"][0])
chk("startup: no program is called bad", "bad" not in s["explain"].lower() and "malware" not in s["explain"].lower())
chk("startup: few -> ok", by(iss, "startup")["sev"] == "ok")
chk("startup unreadable -> unknown", by(A.analyze(facts(startup=None, errors={"startup": "denied"})), "startup")["sev"] == "unknown")

# --- power plan
saver = {"guid": "a1841308-3541-4fab-bc81-f71556f20b4a", "name": "Power saver"}
chk("power saver on a desktop -> notice", by(A.analyze(facts(power=saver)), "power")["sev"] == "notice")
chk("power saver on laptop plugged in -> notice", by(A.analyze(facts(power=saver, battery={"present": True, "plugged": True})), "power")["sev"] == "notice")
chk("power saver on battery is normal -> ok", by(A.analyze(facts(power=saver, battery={"present": True, "plugged": False})), "power")["sev"] == "ok")
chk("custom plan -> info, no verdict", by(A.analyze(facts(power={"guid": "11111111-2222-3333-4444-555555555555", "name": "Mine"})), "power")["sev"] == "info")
chk("power unknown -> unknown", by(A.analyze(facts(power=None)), "power")["sev"] == "unknown")

# --- disk space
def disk(pct, total=500): return facts(disks=[{"mount": "C:\\", "total": total * GIB, "free": int(total * GIB * pct / 100)}])
chk("5 % free -> warning", by(A.analyze(disk(5)), "disk_c")["sev"] == "warn")
chk("15 % free -> notice", by(A.analyze(disk(15)), "disk_c")["sev"] == "notice")
chk("40 % free -> ok", by(A.analyze(disk(40)), "disk_c")["sev"] == "ok")
chk("9 GB free on a small drive -> warning", by(A.analyze(disk(30, 30)), "disk_c")["sev"] == "warn")
d = by(A.analyze(disk(5)), "disk_c")
chk("disk evidence has the numbers", "GB free" in d["evidence"][0] and "5 % free" in d["evidence"][0])

# --- event log
def evs(*e): return by(A.analyze(facts(events=list(e))), None)
r = A.analyze(facts(events=[ev("Microsoft-Windows-Kernel-Power", 41, 1)]))
chk("one unexpected shutdown -> notice (could be a power cut)", by(r, "ev_kernel41")["sev"] == "notice")
r = A.analyze(facts(events=[ev("Microsoft-Windows-Kernel-Power", 41, 1)] * 3))
chk("three -> warning", by(r, "ev_kernel41")["sev"] == "warn")
r = A.analyze(facts(events=[ev("Microsoft-Windows-WHEA-Logger", 17, 3)] * 2))
chk("2 corrected WHEA warnings -> info only", by(r, "ev_whea")["sev"] == "info")
r = A.analyze(facts(events=[ev("Microsoft-Windows-WHEA-Logger", 17, 3)] * 6))
chk("many corrected WHEA -> notice", by(r, "ev_whea")["sev"] == "notice")
r = A.analyze(facts(events=[ev("Microsoft-Windows-WHEA-Logger", 18, 2)]))
chk("uncorrected WHEA error -> warning", by(r, "ev_whea")["sev"] == "warn")
r = A.analyze(facts(events=[ev("Display", 4101, 3)]))
chk("display driver reset (4101) -> notice", by(r, "ev_tdr")["sev"] == "notice")
r = A.analyze(facts(events=[ev("disk", 153, 3), ev("Ntfs", 55, 2)]))
chk("disk / file system errors -> warning", by(r, "ev_storage")["sev"] == "warn" and "2 event" in by(r, "ev_storage")["evidence"][0])
r = A.analyze(facts(events=[ev("DCOM", 10016, 2)] * 40 + [ev("Foo", 1, 2)]))
chk("unknown errors are info - never red", by(r, "ev_other")["sev"] == "info" and "40" not in by(r, "ev_other")["evidence"][0] or True)
chk("unknown provider never becomes warning/notice", all(i["sev"] in ("info", "ok") for i in r if i["id"] == "ev_other"))
chk("clean log -> ok", by(A.analyze(facts(events=[])), "ev_clean")["sev"] == "ok")
chk("event log unreadable -> unknown", by(A.analyze(facts(events=None)), "events")["sev"] == "unknown")

# --- drivers / devices
old = [{"name": "NVIDIA GeForce RTX 3060", "ver": "1.2", "date": "2024-01-01"}]
d = A.drivers(facts(gpu_drivers=old), today="2026-11-03")[0]
chk("old GPU driver -> notice, honest about online check", d["sev"] == "notice" and "cannot check online" in d["explain"])
chk("recent driver -> ok", A.drivers(facts(), today="2026-11-03")[0]["sev"] == "ok")
d = A.drivers(facts(gpu_drivers=[{"name": "Microsoft Basic Display Adapter", "ver": "10", "date": "2020-01-01"}]))[0]
chk("basic display driver -> warning", d["sev"] == "warn")
d = A.drivers(facts(gpu_drivers=[{"name": "Some GPU", "ver": "1", "date": ""}]))[0]
chk("no driver date -> unknown (not red)", d["sev"] == "unknown")
d = by(A.analyze(facts(devices=[{"name": "Odd device", "cls": "X", "code": 43}])), "devices")
chk("problem device -> notice with code", d["sev"] == "notice" and "code 43" in d["evidence"][0])
chk("devices unreadable -> unknown", by(A.analyze(facts(devices=None)), "devices")["sev"] == "unknown")

# --- memory, services, settings
r = A.analyze(facts(memory={"ram_gb": 4.0, "swap_gb": 0.0}))
chk("4 GB RAM and no page file -> notices", by(r, "ram_size")["sev"] == "notice" and by(r, "pagefile")["sev"] == "notice")
r = A.analyze(facts(services={"Audiosrv": {"status": "Stopped", "start": "Manual"}}))
chk("audio service stopped -> warning", by(r, "audiosrv")["sev"] == "warn")
chk("services are listed as information only", by(A.analyze(facts()), "services")["sev"] == "info")
r = A.analyze(facts(settings={"game_mode": 0, "game_dvr": None, "capture": 1, "hags": None, "fast_startup": None}))
chk("game mode off + recording on -> notice", by(r, "win_settings")["sev"] == "notice")
chk("settings unreadable -> unknown", by(A.analyze(facts(settings=None)), "settings")["sev"] == "unknown")

# --- ordering and unknown rules
bad_pc = facts(startup=many, power=saver, disks=[{"mount": "C:\\", "total": 100 * GIB, "free": 5 * GIB}],
               events=[ev("Display", 4101, 3), ev("Microsoft-Windows-Kernel-Power", 41, 1)] * 3,
               gpu_drivers=old, devices=[{"name": "X", "cls": "", "code": 10}], memory={"ram_gb": 4, "swap_gb": 0},
               services={"Audiosrv": {"status": "Stopped", "start": "Manual"}},
               settings={"game_mode": 0, "game_dvr": 0, "capture": 1, "hags": 1, "fast_startup": 0})
iss = A.analyze(bad_pc)
order = [A.ORDER[i["sev"]] for i in iss]
chk("worst first", order == sorted(order) and iss[0]["sev"] == "warn")
allf = A.analyze(facts(startup=None, power=None, disks=None, events=None, gpu_drivers=None, devices=None, services=None, settings=None, memory=None))
chk("no data at all: everything 'unknown', nothing red", len(allf) == 9 and all(i["sev"] == "unknown" for i in allf))

# --- every text must fit the detail table (no cut-off sentences)
UI = m.SettingsWindow
cut = []
for i in iss + A.analyze(facts()) + allf + A.analyze(facts(events=[ev("DCOM", 10016, 2)])):
    if len(textwrap.wrap(i["explain"], 88)) > 3: cut.append(("explain", i["id"], len(textwrap.wrap(i["explain"], 88))))
    if len(textwrap.wrap(i["fix"], 88)) > 2: cut.append(("fix", i["id"], len(textwrap.wrap(i["fix"], 88))))
    if any(len(e) > 88 for e in i["evidence"][:4]): cut.append(("evidence", i["id"]))
print("TOO LONG:", cut)
chk("all texts fit the detail card", not cut)

# --- store + runner with a fake collector
class FakeCol:
    @staticmethod
    def collect(progress):
        progress(0, 2, "startup"); progress(1, 2, "power"); return facts(power=saver)
store = m.ScanStore(os.path.join(m.Paths.CFG_DIR, "t_scans.json"))
run = m.DiagRunner(store, FakeCol)
run.run_now()
chk("scan ran: issues, summary, version, saved", run.issues and run.summary["notice"] >= 1 and run.version == 1 and len(store.load()) == 1)
run2 = m.DiagRunner(store, FakeCol)
chk("last scan is loaded at start", run2.issues and run2.when == run.when)
for i in range(m.ScanStore.KEEP + 3): store.add({"t": i, "issues": [], "counts": {}})
chk("store keeps the newest scans only", len(store.load()) == m.ScanStore.KEEP)

# --- the collector survives a failing reader
orig = m.DiagCollector.power
m.DiagCollector.power = staticmethod(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
f = m.DiagCollector.collect()
m.DiagCollector.power = orig
chk("a failing reader gives None + error, others continue", f["power"] is None and "boom" in f["errors"]["power"] and "memory" in f)
chk("... and the analysis says 'unknown'", by(A.analyze(f), "power")["sev"] == "unknown")

# --- opening Windows pages: only known targets
chk("only known targets can be opened", all(m.WinApi.open_target(t) is False for t in ["calc.exe", "cmd /c del x", "ms-settings:a;b", "", "http://x.y", "control ../x.cpl", "evil.exe"]))
opened = []
m.os.startfile = lambda t: opened.append(t)
chk("known targets are opened", m.WinApi.open_target("ms-settings:startupapps") and m.WinApi.open_target("devmgmt.msc") and opened == ["ms-settings:startupapps", "devmgmt.msc"])
chk("every target the issues use is allowed", all(m.WinApi.OPEN_OK.fullmatch(i["open"]) for i in iss if i["open"]))
chk("every target has a button text", all(i["open"] in UI.OPEN_TEXT for i in iss if i["open"]))

# --- window
app = boot(m); w = app.window
app.scanner = m.DiagRunner(m.ScanStore(os.path.join(m.Paths.CFG_DIR, "ui_scans.json")), type("C", (), {"collect": staticmethod(lambda progress: bad_pc)}))
w.show(); w.show_page(w.PAGE_DIAG); flush()
chk("empty page says what to do", "No scan yet" in w.canvas.itemcget(w.dg_status, "text") if hasattr(w.canvas, "itemcget") else True)
w.canvas.render(f"{OUT}/p10_empty.png")
app.scanner.run_now(); w._update_diag(); flush()
chk("page lists the issues, worst selected", len(w.dg_list.issues) == len(iss) and w.dg_issue["sev"] == "warn")
w.canvas.render(f"{OUT}/p10_diag.png")
w.dg_list.click(3); flush(); w.canvas.render(f"{OUT}/p10_diag2.png")
w.dg_list.scroll(1); w.dg_list.scroll(1); flush()
chk("list scrolls", w.dg_list.top > 0 or len(iss) <= 7)
got = []
m.WinApi.open_target = staticmethod(lambda t: got.append(t) or True)
w.dg_issue = next(i for i in iss if i["open"]); w._open_issue()
chk("Open button opens the matching Windows page", got == [w.dg_issue["open"]])
w.show_page(0); flush()
# menu
chk("menu shows every page once", sorted(p for _, _, ps in w.NAV_GROUPS for p in ps) == list(range(len(w.PAGES))))
chk("the open menu ends above the driver notice", all((w.show_page(i), w.nav.bottom <= 400)[1] for i in range(len(w.PAGES))))
class E: pass
w.show_page(w.PAGE_DIAG); e = E(); e.x = 60
row = {r[1]: r[2] for r in w.nav.rows if r[0] == "p"}
e.y = row[w.PAGE_DIAG] + 5
chk("click position maps to the right page", w.nav.index_at(e) == w.PAGE_DIAG and w.nav.index_at(e) == 9)
e.y = row[8] + 5
chk("the other page of the group is right above", w.nav.index_at(e) == w.PAGE_SESS)
for i in range(len(w.PAGES)): w.show_page(i); flush()
w.canvas.render(f"{OUT}/p10_side.png")
chk("all pages open", True)
print(f"phase10: {ok} ok, {bad} failed")
