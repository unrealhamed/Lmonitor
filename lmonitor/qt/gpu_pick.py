"""Draw Lmonitor's windows on the GPU that drives the screen, not on the game GPU.

On a laptop with two GPUs (Intel / AMD iGPU + NVIDIA dGPU) the screen is usually wired
to the iGPU. Qt may still pick the dGPU; then every frame of Lmonitor is drawn on the
GPU the game needs and copied across to the iGPU (measured on an RTX 4070 laptop:
~20 % GPU copy-engine use and ~300 MB of the game's video memory).

This only sets QT_D3D_ADAPTER_INDEX (read by Qt's Direct3D 11 backend) before the
QApplication exists. Nothing is changed in Windows. Any error: Qt's own choice stays.
"""
import ctypes
import os
from ctypes import wintypes


class _Desc1(ctypes.Structure):
    _fields_ = [("Description", wintypes.WCHAR * 128), ("VendorId", wintypes.UINT),
                ("DeviceId", wintypes.UINT), ("SubSysId", wintypes.UINT),
                ("Revision", wintypes.UINT), ("DedicatedVideoMemory", ctypes.c_size_t),
                ("DedicatedSystemMemory", ctypes.c_size_t),
                ("SharedSystemMemory", ctypes.c_size_t),
                ("LuidLow", wintypes.DWORD), ("LuidHigh", wintypes.LONG),
                ("Flags", wintypes.UINT)]


class _GUID(ctypes.Structure):
    _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD),
                ("d", ctypes.c_ubyte * 8)]


# IID_IDXGIFactory1 {770aae78-f26f-4dba-a829-253c83d1b387}
_IID_FACTORY1 = _GUID(0x770aae78, 0xf26f, 0x4dba,
                      (ctypes.c_ubyte * 8)(0xa8, 0x29, 0x25, 0x3c, 0x83, 0xd1, 0xb3, 0x87))
_SOFTWARE = 2


def _method(obj, index, restype, *argtypes):
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])


def _release(obj):
    if obj:
        _method(obj, 2, wintypes.ULONG)(obj)


def adapters():
    """[(index, name, vendor id, has a screen attached, is software)] in DXGI order."""
    out = []
    factory = ctypes.c_void_p()
    if ctypes.windll.dxgi.CreateDXGIFactory1(ctypes.byref(_IID_FACTORY1),
                                             ctypes.byref(factory)) != 0:
        return out
    try:
        enum1 = _method(factory, 12, ctypes.c_long, wintypes.UINT, ctypes.POINTER(ctypes.c_void_p))
        i = 0
        while i < 16:
            ad = ctypes.c_void_p()
            if enum1(factory, i, ctypes.byref(ad)) != 0:       # DXGI_ERROR_NOT_FOUND: done
                break
            try:
                desc = _Desc1()
                _method(ad, 10, ctypes.c_long, ctypes.POINTER(_Desc1))(ad, ctypes.byref(desc))
                outp = ctypes.c_void_p()
                screen = _method(ad, 7, ctypes.c_long, wintypes.UINT,
                                 ctypes.POINTER(ctypes.c_void_p))(ad, 0, ctypes.byref(outp)) == 0
                _release(outp)
                out.append((i, desc.Description, desc.VendorId, screen,
                            bool(desc.Flags & _SOFTWARE)))
            finally:
                _release(ad)
            i += 1
    finally:
        _release(factory)
    return out


class _DisplayDevice(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]


def screen_gpus():
    """Names of the GPUs that really drive a screen, the main screen's first.

    DXGI cannot tell this on a two-GPU laptop (it lists the screens under the GPU the
    program prefers), but Windows' display-device list names the GPU each screen is
    wired to."""
    names, i = [], 0
    while i < 32:
        d = _DisplayDevice()
        d.cb = ctypes.sizeof(d)
        if not ctypes.windll.user32.EnumDisplayDevicesW(None, i, ctypes.byref(d), 0):
            break
        if d.StateFlags & 0x1:                          # ATTACHED_TO_DESKTOP
            if d.StateFlags & 0x4:                      # PRIMARY_DEVICE
                names.insert(0, d.DeviceString)
            else:
                names.append(d.DeviceString)
        i += 1
    return names


def choose():
    """Index of the GPU wired to the main screen when it differs from Qt's default, else None."""
    ads = [a for a in adapters() if not a[4]]
    if len(ads) < 2:                                    # one GPU: nothing to choose
        return None
    for want in screen_gpus():
        for i, name, _vendor, _screen, _software in ads:
            if name.strip().lower() == want.strip().lower():
                return i
    return None


def apply():
    """Call before QApplication. Returns a short text for the log."""
    if os.environ.get("QT_D3D_ADAPTER_INDEX"):          # set by the user: respect it
        return "QT_D3D_ADAPTER_INDEX set by user"
    try:
        i = choose()
    except Exception as e:                              # never stop the program for this
        return "gpu pick failed: %r" % e
    if i is None:
        return "gpu pick: no adapter with a screen"
    os.environ["QT_D3D_ADAPTER_INDEX"] = str(i)
    return "gpu pick: adapter %d" % i
