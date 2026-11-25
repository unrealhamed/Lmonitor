"""v1.21.1 - Sessions: your own name for a session, the saved picture says where it is,
small grey texts are bigger."""
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
st = E.SessionStore(_os.path.join(E.Paths.CFG_DIR, "t45.db"))
c = {k: [None] * 40 for k in E.SessionRecorder.KEYS}
c["t"] = [i * 2.0 for i in range(40)]
SUM = E.SessionAnalyzer.summarize(c, {"game": "game.exe", "start": time.time(), "end": time.time() + 90}, {"count": 0})
sid = st.save(dict(SUM), {"t": []})
st.rename(sid, "  Before   the new driver ")
chk("renamed (extra spaces tidied)", st.list()[0]["summary"]["title"] == "Before the new driver")
st.update(sid, dict(SUM), {"t": []})
chk("a name given while it still records is kept", st.list()[0]["summary"]["title"] == "Before the new driver")
st.rename(sid, "x" * 100)
chk("at most 60 letters", len(st.list()[0]["summary"]["title"]) == 60)
st.rename(sid, "   ")
chk("empty name: the game's name again", "title" not in st.list()[0]["summary"])
chk("unknown session: nothing happens", st.rename(9999, "a") is False)

from lmonitor.backend import Backend
b = Backend()
b.session_store = st
st.rename(sid, "My test")
it = b.tools_sessions()["items"][0]
rep = b.session_report(sid)
# 1.21.4: the name is given to the program (all its sessions) - see test_phase48
it = b.tools_sessions()["items"][0]
chk("a session's old own name no longer changes the list (names belong to the program now)", it["game"] == "game")
b.close()

sess = read("lmonitor", "qt", "qml", "pages", "SessionsPage.qml")
chk("pencil to rename, Enter saves, Esc cancels", "tools.programRename(" in sess and "onAccepted: page.saveName()" in sess
    and "Keys.onEscapePressed: page.renaming = false" in sess)
chk("the name box reads normally in Persian", "xScale: Tr.rtl ? -1 : 1" in sess)
chk("saved picture: its place is written, can be copied, and a Show in folder button",
    '"Picture saved here:"' in sess and "selectByMouse: true; text: page.saved" in sess and "tools.showFile(page.saved)" in sess)
chk("Explorer is not opened by itself any more", "page.saved = path; tools.showFile" not in sess)
chk("small texts 12 px (was 11)", "readonly property int fsSmall: 12" in read("lmonitor", "qt", "qml", "Lmonitor", "Tokens.qml"))
import re
small = [f for f in ("SessionsPage.qml", "StoragePage.qml", "OptimizerPage.qml", "About.qml", "PersonalizePage.qml")
         if re.search(r"Tokens\.dim[^\n]*pixelSize: (9|10)\b|pixelSize: (9|10)\b[^\n]*Tokens\.dim", read("lmonitor", "qt", "qml", "pages", f))]
chk("no grey text under 11 px on these pages %s" % (small or ""), not small)
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
chk("Persian texts", all(('"%s":' % k) in fa for k in ("Picture saved here:", "Show in folder", "Save", "Cancel")))
chk("version 1.21.1 or newer", tuple(map(int, E.AppInfo.VERSION.split("."))) >= (1, 21, 1))
print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
