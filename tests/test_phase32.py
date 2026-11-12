"""v1.17.8 - MSI Afterburner's overlay was drawn inside Lmonitor's own windows.

Seen in the author's video: Afterburner's overlay text appeared inside Lmonitor's main
window, its graph overlay and its overlay bar, jumping between them. Afterburner's overlay
is drawn by RivaTuner Statistics Server (RTSS), which hooks every program that draws with
DirectX - Lmonitor's windows too. RTSS ships "do not hook" profiles for other monitoring
tools (HWiNFO, FPS Monitor, Discord, Afterburner): Profiles/<program>.cfg with
[Hooking] EnableHooking = 0. Lmonitor now gets the same."""
import os as _os, sys, tempfile, shutil
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

from lmonitor.engine import RivaTuner

d = tempfile.mkdtemp(prefix="rtss_")
try:
    _os.makedirs(_os.path.join(d, "Profiles"))
    prof = _os.path.join(d, "Profiles", "Lmonitor.exe.cfg")
    chk("no RivaTuner: nothing to do", RivaTuner.exclude(folder="") == "no rtss")
    chk("writes the profile", RivaTuner.exclude(folder=d) == "excluded" and _os.path.exists(prof))
    txt = open(prof, encoding="utf-8").read()
    chk("the same content RivaTuner uses for HWiNFO / Discord", "[Hooking]" in txt and "EnableHooking\t\t= 0" in txt)
    chk("a second time: already done, file unchanged", RivaTuner.exclude(folder=d) == "already"
        and open(prof, encoding="utf-8").read() == txt)
    open(prof, "w", encoding="utf-8").write("[OSD]\nEnableOSD=1\n[Hooking]\nEnableHooking\t\t= 1\n")
    chk("a profile the user made is kept, only hooking is switched off", RivaTuner.exclude(folder=d) == "excluded"
        and "EnableOSD=1" in open(prof, encoding="utf-8").read()
        and "EnableHooking\t\t= 0" in open(prof, encoding="utf-8").read())
    open(prof, "w", encoding="utf-8").write("[OSD]\nEnableOSD=1\n")
    RivaTuner.exclude(folder=d)
    t = open(prof, encoding="utf-8").read()
    chk("a profile without a hooking part gets one", "EnableOSD=1" in t and "[Hooking]" in t and "= 0" in t)
finally:
    shutil.rmtree(d, ignore_errors=True)
chk("RivaTuner's folder is looked up in the registry", "Unwinder" + chr(92) + "RTSS" in read("lmonitor", "engine.py"))
app = read("lmonitor", "qt", "app.py")
chk("done at start for the built Lmonitor.exe (never for python.exe)",
    "RivaTuner.exclude(os.path.basename(sys.executable))" in app
    and 'if getattr(sys, "frozen", False):  # MSI Afterburner' in app)
iss = read("installer", "Lmonitor.iss")
chk("the installer writes it before the first start", r"SaveStringToFile(RtssDir() + '\Profiles\{#AppExe}.cfg'" in iss)
chk("the uninstaller removes it", r"DeleteFile(RtssDir() + '\Profiles\{#AppExe}.cfg')" in iss)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
