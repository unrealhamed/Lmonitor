import os as _os
import sys, io, contextlib, time, os, tempfile
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT, press
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load()
base = tempfile.mkdtemp()
home = os.path.join(base, "Users", "me"); os.makedirs(home)
os.environ["USERPROFILE"] = home; os.environ["HOME"] = home
local = os.path.join(base, "Local"); os.environ["LOCALAPPDATA"] = local
now = time.time(); old = now - 3 * 86400
def mk(p, n, mt=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f: f.truncate(n)
    if mt: os.utime(p, (mt, mt))
# ---- guard
G = m.StorageGuard
chk("game library is protected", G.reason(r"D:\SteamLibrary\steamapps\common\X\big.pak") != "")
chk("saves are protected", G.reason(r"C:\Users\me\Saved Games\X\save1.dat") != "" and G.reason(r"C:\Users\me\AppData\Local\X\Saves\a.sav") != "")
chk("personal folders are protected", G.reason(r"C:\Users\me\Documents\thesis.docx") != "" and G.reason(r"C:\Users\me\Videos\a.mp4") != "")
chk("system/program folders protected", G.reason(r"C:\Program Files\X\a.dll") != "" and G.reason(r"C:\Windows\x.dll") != "")
chk("plain download has no objection", G.reason(r"C:\Users\me\Downloads\setup.iso") == "")
dl = os.path.join(home, "Downloads")
mk(os.path.join(dl, "movie.iso"), 700 * 1024 ** 2)
mk(os.path.join(dl, "Games", "g.bin"), 700 * 1024 ** 2)
mk(os.path.join(home, "Documents", "d.bin"), 700 * 1024 ** 2)
mk(os.path.join(home, "Desktop", "x.bin"), 10)
chk("a file in Downloads is deletable", G.deletable(os.path.join(dl, "movie.iso")))
chk("Downloads\\Games is not", not G.deletable(os.path.join(dl, "Games", "g.bin")))
chk("Documents file is not", not G.deletable(os.path.join(home, "Documents", "d.bin")))
chk("a folder or missing path is not", not G.deletable(dl) and not G.deletable(os.path.join(dl, "nope")))
# ---- caches
log = m.ChangeLog(os.path.join(base, "ch.json")); st = m.Storage(log)
dx = os.path.join(local, "NVIDIA", "DXCache")
mk(os.path.join(dx, "a.bin"), 2000, old); mk(os.path.join(dx, "b.bin"), 500, now)
user_temp = os.path.join(base, "Temp"); mk(os.path.join(user_temp, "t.tmp"), 1000, old)
os.environ["TEMP"] = user_temp
st.scan_caches()
chk("reclaimable is measured before deleting", st.caches["nv_dx"]["old_bytes"] == 2000 and os.path.exists(os.path.join(dx, "a.bin")))
chk("total reclaimable adds up", st.reclaimable() >= 3000)
chk("missing cache folders are just absent", st.caches.get("chrome") is None)
chk("only listed cache folders are accepted", m.StorageCleaner.safe_root(dx) and not m.StorageCleaner.safe_root(os.path.join(dx, "..")) and not m.StorageCleaner.safe_root(home) and not m.StorageCleaner.safe_root(""))
chk("cleaner refuses Downloads", m.StorageCleaner.clean(dl, now)["deleted"] == 0)
r = st.clean_cache("nv_dx")
chk("old cache file removed, new kept", not os.path.exists(os.path.join(dx, "a.bin")) and os.path.exists(os.path.join(dx, "b.bin")) and r["ok"])
chk("clean says it cannot be undone and is logged without undo", "cannot be undone" in r["message"] and log.load()[-1]["kind"] == "storage" and log.load()[-1]["revert"] is None)
chk("unknown cache id is refused", not st.clean_cache("../x")["ok"])
# ---- scans
st.scan_folders([home]); st.scan_large([home])
names = [os.path.basename(d["path"]) for d in st.folders]
chk("big folders sorted by size", names[0] in ("Downloads", "Documents") and "Desktop" in names)
chk("protected folder carries its reason", next(d for d in st.folders if d["path"].endswith("Documents"))["reason"] != "")
lg = {os.path.basename(d["path"]): d for d in st.large}
chk("large files found, small ones not", set(lg) == {"movie.iso", "g.bin", "d.bin"})
chk("only Downloads file is deletable", lg["movie.iso"]["deletable"] and not lg["g.bin"]["deletable"] and not lg["d.bin"]["deletable"])
# ---- recycle
calls = []
m.Storage._to_recycle = staticmethod(lambda p: (calls.append(p), os.remove(p)))
r = st.recycle(os.path.join(home, "Documents", "d.bin"))
chk("recycle refuses a Documents file", not r["ok"] and not calls and os.path.exists(os.path.join(home, "Documents", "d.bin")))
r = st.recycle(os.path.join(dl, "never-scanned.iso"))
chk("recycle refuses a path that was never listed", not r["ok"] and not calls)
r = st.recycle(os.path.join(dl, "movie.iso"))
chk("recycle moves the listed Downloads file", r["ok"] and calls and not os.path.exists(os.path.join(dl, "movie.iso")) and "Recycle Bin" in r["message"])
chk("it leaves the list afterwards", all(not d["path"].endswith("movie.iso") for d in st.large))
mk(os.path.join(dl, "stay.iso"), 600 * 1024 ** 2); st.scan_large([home])
m.Storage._to_recycle = staticmethod(lambda p: None)
r = st.recycle(os.path.join(dl, "stay.iso"))
chk("failed move is reported, file kept", not r["ok"] and os.path.exists(os.path.join(dl, "stay.iso")) and log.load()[-1]["status"] == "failed")
chk("no service/registry code in storage", not any(w in open(_os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "monitor.py")).read() for w in ("Set-Service", "sc config", "rmtree")))
# ---- window
app = boot(m); w = app.window
app.change_log = m.ChangeLog(os.path.join(base, "ui.json")); app.storage = m.Storage(app.change_log)
w.show(); w.show_page(w.PAGE_STORE)
for _ in range(60):
    if not app.storage.busy and app.storage.scanned: break
    time.sleep(0.05)
w._poll_store(); flush()
rows = w.st_list.rows
chk("cleanup tab has group headers and checkbox rows", rows[0].get("header") and any(r.get("check") is not None for r in rows))
chk("recommended items are ticked by default, others not", all(r["check"] for r in rows if r["key"][0] == "cache" and r["key"][1] in m.Storage.RECOMMENDED and r.get("check") is not None) and not any(r["check"] for r in rows if r["key"][0] == "cache" and r["key"][1] not in m.Storage.RECOMMENDED and r.get("check") is not None))
w.canvas.render(f"{OUT}/p12_cleanup.png")
press(w, w.st_list, 1, "row")   # the first item under the header: untick
chk("clicking a row toggles its checkbox", w.st_list.rows[1]["check"] is False)
press(w, w.st_list, 1, "row")
chk("ticked again", w.st_list.rows[1]["check"] is True)
w._store_clean_click()
w.canvas.render(f"{OUT}/p12_confirm.png")
chk("first Clean up click only asks", w.st_clean_pending and os.path.exists(os.path.join(user_temp, "t.tmp")))
w._store_clean_click()
for _ in range(60):
    if not app.storage.busy: break
    time.sleep(0.05)
w._poll_store(); flush()
chk("second click cleans everything ticked in one go", not os.path.exists(os.path.join(user_temp, "t.tmp")) and app.storage.last["ok"] and "location" in app.storage.last["title"])
chk("nothing selected -> nothing happens", (w._store_clean_click(), not app.storage.busy)[1])
for t in (1, 2):
    w.st_seg.select(t); w._pick_store_tab(t)
    for _ in range(100):
        if not app.storage.busy: break
        time.sleep(0.05)
    w._poll_store(); flush(); w.canvas.render(f"{OUT}/p12_tab{t}.png")
chk("tabs fill", app.storage.folders is not None and app.storage.large is not None)
chk("menu fits above the driver notice", all((w.show_page(i), w.nav.bottom <= 400)[1] for i in range(len(w.PAGES))))
for i in range(len(w.PAGES)): w.show_page(i); flush()
w.show_page(w.PAGE_STORE); flush(); w.canvas.render(f"{OUT}/p12_side.png")
print(f"phase12: {ok} ok, {bad} failed")
