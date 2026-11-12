"""v1.17.6 - update notice without pressing a button, and "Start with Windows"."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from lmonitor.engine import Autostart
import xml.dom.minidom as minidom

# ---- start with Windows: a Task Scheduler task (Windows will not start an
# administrator program from the normal "Run" list)
x = Autostart.xml(user="PC\\Me & Co", exe="C:\\Program Files\\Lmonitor\\Lmonitor.exe", args="--startup",
                  cwd="C:\\Program Files\\Lmonitor")
try:
    doc = minidom.parseString(x.replace('encoding="UTF-16"', 'encoding="utf-8"').encode("utf-8"))
    chk("the task file is valid XML (also with & in the user name)", True)
except Exception as e:
    doc = None
    chk("the task file is valid XML (%r)" % e, False)
def val(tag): return doc.getElementsByTagName(tag)[0].firstChild.data if doc else ""
chk("runs at sign-in of this user", doc is not None and len(doc.getElementsByTagName("LogonTrigger")) == 1 and val("UserId") == "PC\\Me & Co")
chk("with administrator rights, no question each time", val("RunLevel") == "HighestAvailable")
chk("also on battery (laptop)", val("DisallowStartIfOnBatteries") == "false" and val("StopIfGoingOnBatteries") == "false")
chk("never stopped after some hours", val("ExecutionTimeLimit") == "PT0S")
chk("starts hidden", val("Command").endswith("Lmonitor.exe") and val("Arguments") == "--startup")
calls = []
real = Autostart._schtasks
Autostart._schtasks = staticmethod(lambda *a: (calls.append(a), (0, ""))[1])
chk("switching on creates the task from the file", Autostart.set(True) == "" and calls[-1][:3] == ("/Create", "/TN", "Lmonitor") and "/XML" in calls[-1])
chk("switching off deletes it", Autostart.set(False) == "" and calls[-1][:3] == ("/Delete", "/TN", "Lmonitor"))
Autostart._schtasks = staticmethod(lambda *a: (1, "ERROR: Access is denied."))
r = Autostart.set(True)
chk("a refusal is reported (never a silent 'on')", r != "" and Autostart.is_on() is False)
Autostart._schtasks = real
chk("the uninstaller removes the task", 'schtasks.exe"; Parameters: "/Delete /TN ""Lmonitor"" /F"' in read("installer", "Lmonitor.iss"))
main = read("lmonitor", "qt", "qml", "Main.qml")
br = read("lmonitor", "qt", "bridge.py")
chk("started by Windows: no window, tray only", "visible: !backend.startHidden" in main and '"--startup" in sys.argv' in br)
chk("hidden start prepares no window data", 'self._ui_visible = "--startup" not in sys.argv' in br)
chk("option on the Personalize page", "backend.setAutostart(v)" in read("lmonitor", "qt", "qml", "pages", "PersonalizePage.qml"))

# ---- update notice
chk("checked at start and every 3 hours", "self._upd_timer.timeout.connect(self._auto_check)" in br and "UPDATE_EVERY_MS = 3 * 3600 * 1000" in br)
chk("a found version is announced once", "d.get(\"version\") != self._told" in br and "self.updateFound.emit(self._told)" in br)
chk("banner on every page with Install / Later", "id: updBar" in main and "backend.installUpdate()" in main and 'Tr.t("Later")' in main)
chk("Later hides it only for that version", "backend.update.version !== win.laterVersion" in main)
chk("message next to the clock", "bridge.updateFound.connect(told)" in read("lmonitor", "qt", "app.py"))
fa = read("lmonitor", "qt", "qml", "Lmonitor", "fa.js")
for s in ("Start with Windows", "Install now", "A new version is available: "):
    chk("Persian text for '%s'" % s, '"%s":' % s in fa)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
