"""v1.17.1 - Lmonitor must not slow games down.

Measured before the fix (RTX 4070 laptop, Intel screen GPU, dashboard open):
the window was drawn on the NVIDIA GPU (~20 % copy engine, ~300 MB video memory)
and kept animating at 144 frames/s even with a full-screen game in front."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

def read(*p): return open(_os.path.join(ROOT, *p), encoding="utf-8").read()

# ---- 1. draw on the GPU that is wired to the screen
from lmonitor.qt import gpu_pick
real_adapters, real_screens = gpu_pick.adapters, gpu_pick.screen_gpus
NV = (0, "NVIDIA GeForce RTX 4070 Laptop GPU", 0x10de, True, False)
IN = (1, "Intel(R) Iris(R) Xe Graphics", 0x8086, False, False)
SW = (2, "Microsoft Basic Render Driver", 0x1414, False, True)
gpu_pick.adapters = lambda: [NV, IN, SW]
gpu_pick.screen_gpus = lambda: ["Intel(R) Iris(R) Xe Graphics"]
chk("laptop: the screen's GPU (Intel) is chosen, not the game GPU", gpu_pick.choose() == 1)
gpu_pick.screen_gpus = lambda: ["NVIDIA GeForce RTX 4070 Laptop GPU"]
chk("screen wired to NVIDIA (MUX / desktop): NVIDIA stays", gpu_pick.choose() == 0)
gpu_pick.adapters = lambda: [NV, SW]
chk("one real GPU: Qt decides (nothing set)", gpu_pick.choose() is None)
gpu_pick.adapters = lambda: [NV, IN]
gpu_pick.screen_gpus = lambda: ["Some Other Adapter"]
chk("no match: Qt decides", gpu_pick.choose() is None)
old = _os.environ.pop("QT_D3D_ADAPTER_INDEX", None)
_os.environ["QT_D3D_ADAPTER_INDEX"] = "5"
chk("a value set by the user is kept", "user" in gpu_pick.apply() and _os.environ["QT_D3D_ADAPTER_INDEX"] == "5")
_os.environ.pop("QT_D3D_ADAPTER_INDEX")
gpu_pick.adapters = lambda: (_ for _ in ()).throw(OSError("no dxgi"))
chk("an error never stops the program", "failed" in gpu_pick.apply()
    and "QT_D3D_ADAPTER_INDEX" not in _os.environ)
gpu_pick.adapters, gpu_pick.screen_gpus = real_adapters, real_screens
if old is not None:
    _os.environ["QT_D3D_ADAPTER_INDEX"] = old
if sys.platform == "win32":
    try:
        ads = gpu_pick.adapters()
        chk("this PC: DXGI adapters can be listed", len(ads) >= 1)
        chk("this PC: at least one screen GPU name", len(gpu_pick.screen_gpus()) >= 1)
    except Exception as e:
        chk("this PC: DXGI listing works (%r)" % e, False)
app = read("lmonitor", "qt", "app.py")
chk("the GPU is chosen before the QApplication exists",
    0 < app.find("gpu_pick.apply()") < app.find("QApplication(sys.argv)"))

# ---- 2. a full-screen game in front: no animation, no window updates, background mode
from lmonitor.engine import WinApi
chk("full-screen check exists", callable(getattr(WinApi, "fullscreen_app", None)))
chk("background mode is gone (v1.17.8: below-normal priority + efficiency mode starved "
    "Lmonitor when a game loaded every core)", getattr(WinApi, "set_background_mode", None) is None)
if sys.platform == "win32":
    WinApi.setup()
    r = WinApi.fullscreen_app()
    chk("full-screen check answers True/False", r in (True, False))
main = read("lmonitor", "qt", "qml", "Main.qml")
chk("chart clock stops while a full-screen program is in front", "!backend.covered" in main)
br = read("lmonitor", "qt", "bridge.py")
chk("the window gets no new data while covered", "shown = self._ui_visible and not covered" in br)
chk("focus changes are still reported", "applicationStateChanged" in app
    and "setAppActive" in br)

# ---- 3. the overlay over a game: no resize / restyle every half second
ow = read("lmonitor", "qt", "qml", "OverlayWindow.qml")
chk("overlay window only grows while numbers change", "function grow()" in ow
    and "width: keepW" in ow and "onWidthChanged" not in ow)
chk("overlay shrinks back when settings change", "onSettingsChanged() { w.fit() }" in ow)
ov = read("lmonitor", "qt", "overlay.py")
chk("blur / corners / on-top are set only when they change", "_look_key" in ov
    and "if key == self._look_key" in ov)

# ---- 4. PresentMon reads only what is used
eng = read("lmonitor", "engine.py")
chk("PresentMon: GPU-work tracking off", '"--no_track_gpu"' in eng)
chk("PresentMon: input tracking off", '"--no_track_input"' in eng)
chk("PresentMon: non-games excluded", '"--exclude"' in eng)

print("\n%d passed, %d failed" % (ok, bad))
sys.exit(1 if bad else 0)
