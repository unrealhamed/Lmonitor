import os as _os
import sys, io, contextlib, time, os, tempfile, json
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
with contextlib.redirect_stdout(io.StringIO()):
    from t_helpers import load, boot, flush, OUT, press
ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)
m = load(); R = m.ReportBuilder
def iss(id_, area, sev, title=None, ev="x"):
    return {"id": id_, "area": area, "title": title or id_, "sev": sev, "evidence": [ev], "explain": "e", "fix": "f", "open": None}
AREAS = R.AREAS
allok = [iss(a.lower(), a, "ok") for a in AREAS]
s = R.score(allok)
chk("all ok -> 100 with full coverage", s["value"] == 100 and s["covered"] == 8)
s = R.score([])
chk("no scan -> no score, honest text", s["value"] is None and "No scan" in s["text"])
bad_ = allok + [iss("w1", "Power", "warn", "Plan"), iss("n1", "Startup", "notice", "Many")]
s = R.score(bad_)
chk("warn -15 and notice -5, each listed with reason", s["value"] == 80 and {d["points"] for d in s["deductions"]} == {15, 5} and all(d["why"] for d in s["deductions"]))
caps = allok + [iss(f"n{i}", "Startup", "notice") for i in range(8)]
chk("per-area cap of 25", R.score(caps)["value"] == 75)
unk = [iss(a.lower(), a, "unknown") for a in AREAS[:3]] + [iss(a.lower(), a, "ok") for a in AREAS[3:]]
s = R.score(unk)
chk("unknown is NOT healthy: counted as uncovered and says so", s["covered"] == 5 and "not counted as healthy" in s["text"] and len(s["unknown"]) == 3)
few = [iss(a.lower(), a, "unknown") for a in AREAS[:6]] + [iss(a.lower(), a, "ok") for a in AREAS[6:]]
s = R.score(few)
chk("too little data -> no score at all", s["value"] is None and "not enough" in s["text"].lower())
allunk = [iss(a.lower(), a, "unknown") for a in AREAS]
chk("everything unknown is never 100", R.score(allunk)["value"] is None)
# compare scans
old = {"t": 1000, "issues": [iss("a", "Power", "warn", "Plan"), iss("b", "Startup", "notice", "Many"), iss("c", "Drivers", "ok", "Drv"), iss("d", "Memory", "ok", "Mem")]}
new = {"t": 2000, "issues": [iss("a", "Power", "ok", "Plan"), iss("b", "Startup", "notice", "Many"), iss("c", "Drivers", "warn", "Drv"), iss("d", "Memory", "ok", "Mem"), iss("e", "Storage", "notice", "Disk")]}
c = R.compare_scans(old, new)
chk("resolved / worse / new / same", c["resolved"] == ["Plan"] and c["worse"] == ["Drv"] and c["new"] == ["Disk"] and c["same"] == 2)
unk_new = {"t": 2000, "issues": [iss("a", "Power", "unknown", "Plan")]}
c = R.compare_scans({"t": 1, "issues": [iss("a", "Power", "warn", "Plan")]}, unk_new)
chk("a warning that became unknown is NOT resolved or better", c["resolved"] == [] and c["better"] == [] and c["unknown"] == ["Plan"])
# sessions
def sm(fps, l1, gt): return {"avg_fps": fps, "low1": l1, "low01": None, "g_temp": [60, gt], "c_temp": [None, None], "findings": []}
rows = R.compare_sessions(sm(100, 60, 70), sm(110, 50, 71))
d = {r["label"]: r for r in rows}
chk("session deltas with verdicts", d["Average FPS"]["verdict"] == "better" and d["1% low FPS"]["verdict"] == "worse" and d["GPU temperature (max)"]["verdict"] == "about the same")
chk("missing data is 'not comparable', not a verdict", d["0.1% low FPS"]["verdict"] == "not comparable" and d["CPU temperature (max)"]["verdict"] == "not comparable")
sess = [{"id": 1, "game": "A", "start": 100, "duration": 600, "summary": sm(100, 60, 70)},
        {"id": 2, "game": "B", "start": 200, "duration": 600, "summary": sm(50, 30, 70)},
        {"id": 3, "game": "A", "start": 300, "duration": 600, "summary": dict(sm(110, 50, 70), findings=[{"sev": "warn", "title": "RAM", "text": "low"}, {"sev": "ok", "title": "VRAM", "text": "ok"}])}]
p = R.latest_session_pair(sess)
chk("pair = latest session and the previous one of the SAME game", p[0]["id"] == 1 and p[1]["id"] == 3)
chk("single session of a game -> no pair", R.latest_session_pair(sess[:2]) is None)
changes = [{"t": 1500, "title": "Disable at startup: X", "before": "Enabled", "after": "Disabled", "status": "applied"},
           {"t": 1600, "title": "Failed one", "status": "failed"}, {"t": 9000, "title": "later", "status": "applied"}]
rep = R.build([old, new], sess, changes, "9.9", now=5000)
chk("changes between the scans listed (applied only)", rep["scan_changes"]["made_between"] == ["Disable at startup: X"])
chk("only problems kept in issues, ok counted", all(i["sev"] != "ok" for i in rep["issues"]) and rep["ok_count"] == 2)
chk("sessions: findings keep only warn/notice/unknown", rep["sessions"][0]["findings"] == [{"sev": "warn", "title": "RAM", "text": "low"}])
# export
evil = iss("x", "Startup", "warn", "<script>alert(1)</script>", r"C:\Users\TestUser\AppData\Roaming\a.exe")
rep2 = R.build([{"t": 1, "issues": allok + [evil]}], [], [], "1")
html_ = R.to_html(rep2); js = R.to_json(rep2)
chk("HTML escapes everything", "<script>alert(1)</script>" not in html_ and "&lt;script&gt;" in html_)
chk("user name hidden in HTML and JSON", "TestUser" not in html_ and "TestUser" not in js and "<user>" in js.replace("\\u003cuser\\u003e", "<user>"))
chk("JSON is valid and has the score", json.loads(js)["score"]["value"] == 85)
chk("HTML says how the score works and that points are our choice", "own choice" in html_ and "never counted as healthy" in html_)
chk("HTML valid-ish and self-contained (no external links)", html_.startswith("<!doctype html>") and "http://" not in html_ and "https://" not in html_ and "<script src" not in html_)
rep3 = R.build([], [], [], "1")
chk("empty data: report still builds, no score", R.to_html(rep3) and rep3["score"]["value"] is None)
# Reports manager saves to a folder
base = tempfile.mkdtemp(); os.environ["USERPROFILE"] = base; os.environ["HOME"] = base
os.makedirs(os.path.join(base, "Documents"))
class S:
    def load(self): return [old, new]
    def list(self): return sess
class L:
    def load(self): return changes
r_ = m.Reports(S(), S(), L())
res = r_.save("html"); res2 = r_.save("json")
chk("HTML and JSON saved under Documents\\Lmonitor Reports", res["ok"] and res["path"].endswith(".html") and "Lmonitor Reports" in res["path"] and res2["path"].endswith(".json") and os.path.getsize(res["path"]) > 500)
try: r_.save("exe"); chk("unknown format refused", False)
except KeyError: chk("unknown format refused", True)
# window
app = boot(m); w = app.window
app.reports = m.Reports(S(), S(), L())
w.show(); w.show_page(w.PAGE_REPORT)
for _ in range(60):
    if not app.reports.busy and app.reports.report: break
    time.sleep(0.05)
w._poll_report(); flush()
chk("score tab lists deductions", any(r["state"].startswith("-") for r in w.rp_list.rows))
w.canvas.render(f"{OUT}/p13_score.png")
for t in (1, 2, 3):
    w.rp_seg.select(t); w._pick_report_tab(t); flush(); w.canvas.render(f"{OUT}/p13_tab{t}.png")
chk("before/after tab has scan and session rows", len(w.rp_list.rows) >= 1)
w.rp_seg.select(3); w._pick_report_tab(3)
press(w, w.rp_list, 0)
for _ in range(60):
    if not app.reports.busy: break
    time.sleep(0.05)
w._poll_report(); flush(); w.canvas.render(f"{OUT}/p13_saved.png")
chk("Save writes a file in one click (it only writes inside the reports folder)", app.reports.last["ok"] and os.path.isfile(app.reports.last["path"]))
chk("menu fits above the driver notice", all((w.show_page(i), w.nav.bottom <= 400)[1] for i in range(len(w.PAGES))))
for i in range(len(w.PAGES)): w.show_page(i); flush()
print(f"phase13: {ok} ok, {bad} failed")
