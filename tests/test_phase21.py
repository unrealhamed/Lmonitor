import os as _os, sys, io, json, hashlib, tempfile
sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from lmonitor import updater as U

ok = bad = 0
def chk(name, cond):
    global ok, bad
    if cond: ok += 1; print("PASS", name)
    else: bad += 1; print("FAIL", name)

SETUP = b"fake installer bytes"
def release(tag="v1.15.3", url=None, size=None, digest=None, pre=False, name="Lmonitor_Setup_1.15.3.exe"):
    a = {"name": name, "size": len(SETUP) if size is None else size,
         "browser_download_url": url or "https://github.com/unrealhamed/Lmonitor/releases/download/%s/%s" % (tag, name)}
    if digest: a["digest"] = digest
    return {"tag_name": tag, "html_url": "https://github.com/unrealhamed/Lmonitor/releases/tag/" + tag,
            "prerelease": pre, "draft": False, "assets": [a]}
def opener(payload):
    return lambda req, timeout=None: io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode())

chk("parse v-prefixed", U.parse_version("v1.15.3") == (1, 15, 3))
chk("parse -dev suffix", U.parse_version("1.15.3-dev") == (1, 15, 3))
chk("parse junk is None", U.parse_version("latest") is None)
chk("compares numbers, not text", U.parse_version("1.10.0") > U.parse_version("1.9.0"))

info = U.latest("1.15.2", opener(release()))
chk("newer release is reported", info and info["version"] == "1.15.3" and info["url"].endswith("Lmonitor_Setup_1.15.3.exe"))
chk("same version -> nothing", U.latest("1.15.3", opener(release())) is None)
chk("older release -> nothing", U.latest("1.16.0", opener(release())) is None)
chk("pre-release is ignored", U.latest("1.15.2", opener(release(pre=True))) is None)
chk("no installer asset -> nothing", U.latest("1.15.2", opener(release(name="notes.txt"))) is None)
chk("foreign download host is refused", U.latest("1.15.2", opener(release(url="https://evil.example/Lmonitor_Setup_1.15.3.exe"))) is None)

good = "sha256:" + hashlib.sha256(SETUP).hexdigest()
d = tempfile.mkdtemp()
p = U.download(U.latest("1.15.2", opener(release(digest=good))), d, opener(SETUP))
chk("download saves the file", open(p, "rb").read() == SETUP)
p2 = U.download(U.latest("1.15.2", opener(release())), d, opener(SETUP))
chk("download works when GitHub gives no digest", _os.path.exists(p2))
def raises(f):
    try: f()
    except U.UpdateError: return True
    return False
chk("wrong SHA-256 is rejected", raises(lambda: U.download(U.latest("1.15.2", opener(release(digest="sha256:" + "0" * 64))), d, opener(SETUP))))
chk("wrong size is rejected", raises(lambda: U.download(U.latest("1.15.2", opener(release(size=5))), d, opener(SETUP))))
chk("bad download leaves no .part file behind", not [f for f in _os.listdir(d) if f.endswith(".part")])

cmd = U.install_command(r"C:\t\setup.exe", r"C:\p\Lmonitor.exe")
chk("install command runs silently, then starts the app", "/SILENT" in cmd and cmd.rstrip().endswith('start "" "C:\\p\\Lmonitor.exe"'))
print("phase21: %d ok, %d failed" % (ok, bad))
