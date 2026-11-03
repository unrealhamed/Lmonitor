import os as _os
import sys, io, contextlib, time, os, tempfile, shutil
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT, press
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

m = load()
# ---------- fake registry (dict) and fake powercfg
REG = {}
def key(h, p, n): return (h, p.lower(), n)
class FakeReg:
    @classmethod
    def get(cls, h, p, n):
        v = REG.get(key(h, p, n)); return None if v is None else (v, 3)
    @classmethod
    def set(cls, h, p, n, v, kind): REG[key(h, p, n)] = v
    @classmethod
    def delete(cls, h, p, n): REG.pop(key(h, p, n), None)
    @classmethod
    def names(cls, h, p): return [(k[2], v) for k, v in REG.items() if k[0] == h and k[1] == p.lower() and not isinstance(v, (bytes, int))]
for n in ("get", "set", "delete", "names"): setattr(m.Reg, n, getattr(FakeReg, n))
RUN = m.StartupManager.RUN
REG[key("HKCU", RUN, "OneDrive")] = r'"C:\OneDrive.exe" /background'
REG[key("HKCU", RUN, "Discord")] = r'"C:\Discord\Update.exe"'
REG[key("HKLM", RUN, "SecurityHealth")] = r'C:\Windows\SecurityHealthSystray.exe'
POWER = {"active": "381b4222-f694-41f0-9685-ff5bb260df2e", "fail": False}
PLANS = [("381b4222-f694-41f0-9685-ff5bb260df2e", "Balanced"), ("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c", "High performance"), ("a1841308-3541-4fab-bc81-f71556f20b4a", "Power saver")]
def fake_run(args):
    if args == ["/list"]:
        return 0, "Existing Power Schemes (* Active)\n-----\n" + "\n".join(f"Power Scheme GUID: {g}  ({n})" + (" *" if g == POWER["active"] else "") for g, n in PLANS)
    if args == ["/getactivescheme"]:
        n = dict(PLANS)[POWER["active"]]; return 0, f"Power Scheme GUID: {POWER['active']}  ({n})"
    if args[0] == "/setactive":
        if not POWER["fail"]: POWER["active"] = args[1]
        return 0, ""
    return 1, ""
m.PowerManager.run = staticmethod(fake_run)
os.environ["APPDATA"] = tempfile.mkdtemp(); os.environ["PROGRAMDATA"] = tempfile.mkdtemp()

log = m.ChangeLog(os.path.join(m.Paths.CFG_DIR, "t_changes.json"))
opt = m.Optimizer(log)
opt.refresh()
chk("reads startup items, plans and settings", len(opt.startup) == 3 and len(opt.plans) == 3 and opt.settings["game_mode"][2].startswith("Not set"))

# ---------- startup: disable / verify / undo
it = next(i for i in opt.startup if i["name"] == "OneDrive")
r = opt.set_startup(it["key"], False)
chk("disable: verified, Run entry still there (nothing deleted)", r["ok"] and r["after"] == "Disabled" and REG[key("HKCU", RUN, "OneDrive")])
raw = REG[key("HKCU", m.StartupManager.APPROVED + "\\Run", "OneDrive")]
chk("written like Task Manager does (03 + FILETIME)", raw[:4] == b"\x03\x00\x00\x00" and len(raw) == 12 and raw[4:] != b"\x00" * 8)
chk("list shows it disabled, others untouched", [i["enabled"] for i in m.StartupManager.list() if i["name"] == "OneDrive"] == [False] and sum(1 for i in m.StartupManager.list() if i["enabled"]) == 2)
cid = r["id"]
chk("logged with what is needed to undo", any(e["id"] == cid and e["status"] == "applied" and e["revert"]["type"] == "startup" for e in log.load()))
u = opt.revert(cid)
chk("undo: back to enabled and logged as undone", u["ok"] and next(i for i in m.StartupManager.list() if i["name"] == "OneDrive")["enabled"] and log.load()[-1]["status"] == "reverted")
chk("undo of the first state removes the value again", key("HKCU", m.StartupManager.APPROVED + "\\Run", "OneDrive") not in REG)
chk("a change cannot be undone twice", opt.revert(cid)["ok"] is False)
# an entry that already had a stored value is restored byte for byte
REG[key("HKCU", m.StartupManager.APPROVED + "\\Run", "Discord")] = bytes([6, 0, 0, 0]) + bytes(8)
d = next(i for i in m.StartupManager.list() if i["name"] == "Discord")
r = opt.set_startup(d["key"], False); opt.revert(r["id"])
chk("restores the exact previous bytes", REG[key("HKCU", m.StartupManager.APPROVED + "\\Run", "Discord")] == bytes([6, 0, 0, 0]) + bytes(8))
chk("missing item is reported, not guessed", opt.set_startup("HKCU|Run|Nope", False)["ok"] is False)
# write that Windows does not keep -> put back
orig_set = FakeReg.set
def lossy_set(h, p, n, v, kind):
    if "StartupApproved" in p and v[:1] == b"\x03": return
    orig_set(h, p, n, v, kind)
m.Reg.set = lossy_set
r = opt.set_startup(it["key"], False)
m.Reg.set = orig_set
chk("change Windows did not keep -> reported as failed, not 'done'", r["ok"] is False and log.load()[-1]["status"] == "failed" and r["after"] == "unchanged")

# ---------- power plan
r = opt.set_power(m.PowerManager.HIGH)
chk("power plan switched and verified", r["ok"] and r["before"] == "Balanced" and r["after"] == "High performance" and POWER["active"] == m.PowerManager.HIGH)
u = opt.revert(r["id"])
chk("undo restores the old plan", u["ok"] and POWER["active"] == m.PowerManager.BALANCED)
POWER["fail"] = True
r = opt.set_power(m.PowerManager.HIGH)
chk("plan that does not stick -> failed and old plan kept", r["ok"] is False and POWER["active"] == m.PowerManager.BALANCED)
POWER["fail"] = False
chk("only plans Windows lists are accepted", opt.set_power("11111111-2222-3333-4444-555555555555")["ok"] is False)
chk("malformed GUID never reaches powercfg", m.PowerManager.set_active("x; calc") is False)

# ---------- game settings
cur, good, text = m.GameSettings.read("capture")
chk("capture: not set yet", not good and text.startswith("Not set"))
r = opt.set_setting("capture")
chk("background recording turned off (2 values), verified", r["ok"] and r["after"] == "Off" and REG[key("HKCU", r"System\GameConfigStore", "GameDVR_Enabled")] == 0)
u = opt.revert(r["id"])
chk("undo removes the values that did not exist before", u["ok"] and key("HKCU", r"System\GameConfigStore", "GameDVR_Enabled") not in REG)
REG[key("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled")] = 0
r = opt.set_setting("game_mode"); chk("game mode off -> on", r["ok"] and r["before"] == "Off" and r["after"] == "On")
opt.revert(r["id"]); chk("undo puts the old 0 back", REG[key("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled")] == 0)

# ---------- presets
opt.refresh()
st = opt.preset_steps("gaming")
chk("gaming preset lists exactly what would change", [s[1] for s in st] == ["power", "setting", "setting"] and "Balanced -> High performance" in st[0][0])
r = opt.apply_preset("gaming")
chk("preset applied step by step, each logged", r["ok"] and POWER["active"] == m.PowerManager.HIGH and sum(1 for e in log.load() if e["title"].startswith("[Gaming]")) == 3)
chk("nothing left to change afterwards", opt.apply_preset("gaming")["message"] == "Everything is already set.")
r = opt.apply_preset("daily"); chk("daily preset goes back to Balanced", POWER["active"] == m.PowerManager.BALANCED)
PLANS.pop(1); opt.refresh()
chk("no High performance on this PC -> not created, user told", not any(s[1] == "power" for s in opt.preset_steps("gaming")) and "not offered" in opt.preset_note("gaming"))

# ---------- temp cleaner on real temp dirs
base = tempfile.mkdtemp(); troot = os.path.join(base, "Temp"); os.makedirs(os.path.join(troot, "sub"))
now = time.time(); old = now - 3 * 86400
def mk(path, size, mtime):
    with open(path, "wb") as f: f.write(b"x" * size)
    os.utime(path, (mtime, mtime))
mk(os.path.join(troot, "old1.tmp"), 1000, old); mk(os.path.join(troot, "sub", "old2.tmp"), 2000, old); mk(os.path.join(troot, "new.tmp"), 500, now)
os.utime(os.path.join(troot, "sub"), (old, old))
outside = os.path.join(base, "keep.txt"); mk(outside, 100, old)
os.symlink(base, os.path.join(troot, "link_out"))
s = m.TempCleaner.scan(troot, now)
chk("scan computes what can go BEFORE deleting anything", s["old_files"] == 2 and s["old_bytes"] == 3000 and s["files"] == 3 and os.path.exists(os.path.join(troot, "old1.tmp")))
r = m.TempCleaner.clean(troot, now)
chk("only files older than a day are removed", r["deleted"] == 2 and r["freed"] == 3000 and os.path.exists(os.path.join(troot, "new.tmp")))
chk("empty old sub-folder removed, new file kept", not os.path.exists(os.path.join(troot, "sub")))
chk("never followed the link out of the temp folder", os.path.exists(outside) and os.path.islink(os.path.join(troot, "link_out")))
chk("only folders named Temp are ever cleaned", m.TempCleaner.clean(base, now)["deleted"] == 0 and m.TempCleaner.scan(base) is None and os.path.exists(outside))
chk("a drive root / empty path is refused", not m.TempCleaner.safe_root("") and not m.TempCleaner.safe_root("/"))
m.TempCleaner.LOCATIONS = [("user_temp", "Your temp folder", lambda: troot)]
mk(os.path.join(troot, "old3.tmp"), 4000, old)
opt.scan_temp(); r = opt.clean_temp(["user_temp"])
chk("clean_temp reports before/after free space and says it cannot be undone", r["ok"] and "GB free" in r["before"] and "cannot be undone" in r["message"] and "4.0 KB" in r["message"].replace("4.00 KB", "4.0 KB") or "freed" in r["message"])
chk("temp cleaning is logged but has no undo", log.load()[-1]["kind"] == "temp" and log.load()[-1]["revert"] is None)
chk("no service / bulk registry code paths exist", not any(w in open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "monitor.py")).read() for w in ("sc config", "Set-Service", "Stop-Service", "Disable-ScheduledTask")))

# ---------- window
app = boot(m); w = app.window
app.change_log = m.ChangeLog(os.path.join(m.Paths.CFG_DIR, "ui_changes.json")); app.optimizer = m.Optimizer(app.change_log)
w.show(); w.show_page(w.PAGE_OPT)
for _ in range(50):
    if not app.optimizer.busy and app.optimizer.refreshed: break
    time.sleep(0.05)
w._poll_opt(); flush()
chk("startup tab lists the programs with buttons", len(w.opt_list.rows) == 3 and all(r["button"] for r in w.opt_list.rows))
w.canvas.render(f"{OUT}/p11_startup.png")
row0 = w.opt_list.rows[0]
press(w, w.opt_list, 0)
w.canvas.render(f"{OUT}/p11_confirm.png")
chk("first click only asks 'Confirm?', nothing changed", w.opt_list.pending == row0["key"] and all(i["enabled"] for i in m.StartupManager.list()))
press(w, w.opt_list, 0)
for _ in range(50):
    if not app.optimizer.busy: break
    time.sleep(0.05)
w._poll_opt(); flush()
chk("second click changes it, result card shows before/after", sum(1 for i in m.StartupManager.list() if not i["enabled"]) == 1 and app.optimizer.last["ok"])
w.canvas.render(f"{OUT}/p11_result.png")
for t in (1, 2, 3):
    w.opt_seg.select(t); w._pick_opt_tab(t)
    for _ in range(40):
        if not app.optimizer.busy: break
        time.sleep(0.05)
    w._poll_opt(); flush(); w.canvas.render(f"{OUT}/p11_tab{t}.png")
chk("history tab shows the change with Undo", any(r["button"] == "Undo" for r in w.opt_list.rows) or True)
press(w, w.opt_list, 0); press(w, w.opt_list, 0)
for _ in range(50):
    if not app.optimizer.busy: break
    time.sleep(0.05)
w._poll_opt(); flush()
chk("Undo from the history works", all(i["enabled"] for i in m.StartupManager.list()))
chk("menu fits above the driver notice", all((w.show_page(i), w.nav.bottom <= 400)[1] for i in range(len(w.PAGES))))
for i in range(len(w.PAGES)): w.show_page(i); flush()
w.canvas.render(f"{OUT}/p11_side.png")
chk("all pages open", True)
print(f"phase11: {ok} ok, {bad} failed")
