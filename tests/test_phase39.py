"""v1.18.6 - "What's new" after an update.

After installing an update that added something, a box opens once in the middle of the
window (the window behind it is blurred) and shows each change with a small animation.
A new install shows nothing; closing the box remembers the version (settings
"seen_version"); the About page can open it again. For a later feature release only a new
entry in engine.WhatsNew.ENTRIES (+ Persian texts in fa.js) is needed."""
import os as _os, sys, json
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
W = E.WhatsNew

# ---- what is shown
p = W.pending("", "1.18.6")
chk("update from a version that never saw it: shown", p is not None and p["version"] == "1.18.5"
    and p["since"] == "1.18.0" and len(p["slides"]) >= 3)
chk("already seen: nothing", W.pending("1.18.5", "1.18.6") is None and W.pending("1.18.6", "1.18.6") is None)
chk("an entry newer than the running program is not shown", W.pending("", "1.18.4") is None)
chk("every slide has a picture, a kind, a title and a text",
    all(s["art"] and s["kind"] in ("new", "fix") and s["title"] and s["text"] for s in p["slides"]))
old = W.ENTRIES
W.ENTRIES = ({"version": "1.21.0", "since": "1.20.0", "slides": ({"art": "x", "kind": "new", "title": "B", "text": "b"},)},
             {"version": "1.20.0", "since": "1.19.0", "slides": ({"art": "x", "kind": "new", "title": "A", "text": "a"},)}) + old
try:
    q = W.pending("1.19.0", "1.21.0")
    chk("two updates skipped: both shown, newest first", [s["title"] for s in q["slides"]] == ["B", "A"]
        and q["version"] == "1.21.0" and q["since"] == "1.19.0")
    chk("only the missed one", [s["title"] for s in W.pending("1.20.0", "1.21.0")["slides"]] == ["B"])
finally:
    W.ENTRIES = old

# ---- new install / update / seen (the test runner gives every test a new APPDATA)
from lmonitor.backend import Backend
cfg = E.Paths.CFG_FILE
if _os.path.exists(cfg):
    _os.remove(cfg)
b = Backend()
chk("new install: nothing shown, version remembered", b.whats_new() is None
    and b.settings["seen_version"] == E.AppInfo.VERSION and _os.path.exists(cfg))
json.dump({"on": True}, open(cfg, "w", encoding="utf-8"))          # settings of an older version
b2 = Backend()
chk("update (old settings, nothing seen): shown", b2.settings.existed and (b2.whats_new() or {}).get("slides"))
b2.whats_new_seen()
chk("closing it is saved", json.load(open(cfg, encoding="utf-8")).get("seen_version") == E.AppInfo.VERSION)
chk("next start: not shown again", Backend().whats_new() is None)
b2.reset_settings()
chk("'Reset settings' does not bring it back", b2.settings["seen_version"] == E.AppInfo.VERSION)

# ---- the window
main = read("lmonitor", "qt", "qml", "Main.qml")
box = read("lmonitor", "qt", "qml", "components", "WhatsNew.qml")
art = read("lmonitor", "qt", "qml", "components", "WhatsNewArt.qml")
chk("the window behind is blurred (not with the software renderer)", "MultiEffect { blurEnabled: true" in main
    and "GraphicsInfo.api !== GraphicsInfo.Software" in main)
chk("shown only while the window is visible, saved when closed", "shown && !wnDone" in main
    and "backend.whatsNewDone()" in main)
chk("Skip, Next, Back, Got it; Esc and arrow keys", all(x in box for x in ('"Skip"', '"Next"', '"Back"', '"Got it"',
    "Keys.onEscapePressed", "Keys.onRightPressed")))
chk("every picture of the list exists", all(('art.kind === "%s"' % s["art"]) in art for s in p["slides"]))
chk("the pictures only move while their slide is open", "running: slide.on" in box and "running: art.running" in art)
chk("About can open it again", "showWhatsNew()" in read("lmonitor", "qt", "qml", "pages", "About.qml"))
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
missing = [s[k][:40] for s in p["slides"] for k in ("title", "text") if ('"%s":' % s[k]) not in fa]
chk("Persian text for every slide %s" % (missing or ""), not missing)
chk("the build keeps Qt's effects module", "QtQuick/Effects/*" in read("tools", "trim_build.py")
    and "Qt6QuickEffects.dll" in read("tools", "trim_build.py"))
chk("version 1.18.6 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 18, 6))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
